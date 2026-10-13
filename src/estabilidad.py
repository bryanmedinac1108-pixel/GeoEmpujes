"""Motor de estabilidad externa para muros de contención.

Convención geométrica
--------------------
* Se analiza una franja de muro de 1.00 m de longitud.
* x = 0 se ubica en el extremo exterior de la puntera.
* x = B se ubica en el extremo exterior del talón.
* Los pesos se expresan en kN/m y los momentos en kN·m/m.
* Las presiones de contacto se expresan en kPa (= kN/m²).

La función ``evaluar_estabilidad`` conserva los cinco argumentos utilizados
por la interfaz V.2.0. Los argumentos nuevos son opcionales para no romper la
integración mientras los demás módulos del proyecto son actualizados.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Optional


TOLERANCIA = 1.0e-12


def criterios_norma_e050(condicion: str = "estatica") -> dict[str, Any]:
    """Devuelve los factores mínimos aplicables de la Norma E.050.

    Numeral 39.13.6: volteo y deslizamiento.
    Artículo 21: falla por corte/capacidad portante de la cimentación.
    """
    texto = str(condicion).strip().lower()
    for original, reemplazo in (("á", "a"), ("é", "e"), ("í", "i"),
                                ("ó", "o"), ("ú", "u")):
        texto = texto.replace(original, reemplazo)
    texto = texto.replace("_", "-").replace(" ", "-")

    if texto in {"estatica", "estatico"}:
        return {
            "condicion": "Estática",
            "fs_volteo": 1.50,
            "fs_deslizamiento": 1.50,
            "fs_capacidad": 3.00,
        }
    if texto in {
        "pseudo-dinamica", "pseudo-dinamico", "pseudodinamica",
        "pseudodinamico", "sismica", "sismico",
    }:
        return {
            "condicion": "Pseudodinámica",
            "fs_volteo": 1.25,
            "fs_deslizamiento": 1.25,
            "fs_capacidad": 2.50,
        }
    raise ValueError(
        "condicion debe ser 'estatica' o 'pseudodinamica'."
    )


def _criterio_aplicable(
    nombre: str, valor_usuario: Optional[float], minimo_norma: float
) -> float:
    """Permite adoptar un valor más exigente, pero nunca menor a la norma."""
    if valor_usuario is None:
        return minimo_norma
    valor = _numero(nombre, valor_usuario, 0.0)
    return max(valor, minimo_norma)


def _numero(nombre: str, valor: Any, minimo: Optional[float] = None) -> float:
    """Convierte un dato a float y valida que sea finito y admisible."""
    try:
        numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{nombre} debe ser un número.") from exc

    if not math.isfinite(numero):
        raise ValueError(f"{nombre} debe ser un número finito.")
    if minimo is not None and numero < minimo:
        raise ValueError(f"{nombre} debe ser mayor o igual que {minimo}.")
    return numero


def _campo(objeto: Any, nombre: str, predeterminado: Any = None) -> Any:
    """Lee un campo tanto de una clase (dataclass) como de un diccionario."""
    if isinstance(objeto, dict):
        return objeto.get(nombre, predeterminado)
    return getattr(objeto, nombre, predeterminado)


def calcular_cargas_geometricas(
    altura_muro: float,
    espesor_superior: float,
    espesor_inferior: float,
    ancho_puntera: float,
    ancho_talon: float,
    espesor_zapata: float,
    gamma_concreto: float = 24.0,
    altura_suelo_talon: Optional[float] = None,
    gamma_suelo_talon: Optional[float] = None,
    altura_suelo_puntera: float = 0.0,
    gamma_suelo_puntera: Optional[float] = None,
) -> list[dict[str, float | str]]:
    """Calcula pesos propios y sus brazos a partir de una geometría simple.

    La pantalla se idealiza como rectángulo más triángulo. El trasdós se
    considera vertical y alineado con el borde posterior del espesor inferior.
    El suelo sobre talón/puntera se idealiza como un bloque rectangular.

    Esta función devuelve diccionarios compatibles con ``evaluar_estabilidad``.
    También se pueden seguir usando objetos ``CargaVertical`` de modelos.py.
    """
    h = _numero("altura_muro", altura_muro, 0.0)
    ts = _numero("espesor_superior", espesor_superior, 0.0)
    ti = _numero("espesor_inferior", espesor_inferior, 0.0)
    bp = _numero("ancho_puntera", ancho_puntera, 0.0)
    bt = _numero("ancho_talon", ancho_talon, 0.0)
    ez = _numero("espesor_zapata", espesor_zapata, 0.0)
    gc = _numero("gamma_concreto", gamma_concreto, 0.0)

    if ti < ts:
        raise ValueError("espesor_inferior no puede ser menor que espesor_superior.")
    if h <= 0.0 or ti <= 0.0 or ez <= 0.0:
        raise ValueError("La altura, el espesor inferior y la zapata deben ser mayores que cero.")

    ancho_base = bp + ti + bt
    if ancho_base <= 0.0:
        raise ValueError("El ancho total de la base debe ser mayor que cero.")

    cargas: list[dict[str, float | str]] = []

    # Zapata rectangular completa.
    area_zapata = ancho_base * ez
    cargas.append({
        "nombre": "Peso de la zapata",
        "peso": area_zapata * gc,
        "brazo_x": ancho_base / 2.0,
    })

    # Pantalla = rectángulo de espesor superior + ensanche triangular frontal.
    area_rectangulo = ts * h
    if area_rectangulo > 0.0:
        cargas.append({
            "nombre": "Pantalla rectangular",
            "peso": area_rectangulo * gc,
            "brazo_x": bp + ti - ts / 2.0,
        })

    base_triangulo = ti - ts
    area_triangulo = 0.5 * base_triangulo * h
    if area_triangulo > 0.0:
        cargas.append({
            "nombre": "Ensanche triangular de la pantalla",
            "peso": area_triangulo * gc,
            # El vértice superior está junto al rectángulo; el centroide queda
            # a 2/3 de la base medidos desde la cara frontal de la pantalla.
            "brazo_x": bp + 2.0 * base_triangulo / 3.0,
        })

    if altura_suelo_talon is not None and gamma_suelo_talon is not None:
        hs_t = _numero("altura_suelo_talon", altura_suelo_talon, 0.0)
        gs_t = _numero("gamma_suelo_talon", gamma_suelo_talon, 0.0)
        if bt > 0.0 and hs_t > 0.0:
            cargas.append({
                "nombre": "Suelo sobre el talón",
                "peso": bt * hs_t * gs_t,
                "brazo_x": bp + ti + bt / 2.0,
            })

    hs_p = _numero("altura_suelo_puntera", altura_suelo_puntera, 0.0)
    if gamma_suelo_puntera is not None:
        gs_p = _numero("gamma_suelo_puntera", gamma_suelo_puntera, 0.0)
        if bp > 0.0 and hs_p > 0.0:
            cargas.append({
                "nombre": "Suelo sobre la puntera",
                "peso": bp * hs_p * gs_p,
                "brazo_x": bp / 2.0,
            })

    return cargas


def calcular_sumatorias(fuerzas_verticales: Iterable[Any]) -> dict[str, Any]:
    """Suma las cargas verticales y sus momentos respecto a la puntera."""
    peso_total = 0.0
    momento_resistente = 0.0
    detalle = []

    for indice, fuerza in enumerate(fuerzas_verticales, start=1):
        nombre = str(_campo(fuerza, "nombre", f"Carga {indice}"))
        peso = _numero(f"peso de {nombre}", _campo(fuerza, "peso"), 0.0)
        brazo = _numero(f"brazo_x de {nombre}", _campo(fuerza, "brazo_x"), 0.0)
        momento = peso * brazo
        peso_total += peso
        momento_resistente += momento
        detalle.append({
            "nombre": nombre,
            "peso": peso,
            "brazo_x": brazo,
            "momento": momento,
        })

    if peso_total <= TOLERANCIA:
        raise ValueError("La suma de cargas verticales debe ser mayor que cero.")

    return {
        "peso_total": peso_total,
        "momento_resistente": momento_resistente,
        "detalle": detalle,
    }


def verificar_volteo(
    momento_resistente: float,
    momento_actuante: float,
    fs_requerido: float = 1.5,
) -> dict[str, Any]:
    """Calcula FSv = momentos resistentes / momentos actuantes."""
    mr = _numero("momento_resistente", momento_resistente, 0.0)
    ma = _numero("momento_actuante", momento_actuante, 0.0)
    fs_req = _numero("fs_volteo_requerido", fs_requerido, 0.0)
    fs = math.inf if ma <= TOLERANCIA else mr / ma
    return {
        "momento_resistente": mr,
        "momento_actuante": ma,
        "fs": fs,
        "fs_requerido": fs_req,
        "cumple": fs >= fs_req,
    }


def verificar_deslizamiento(
    fuerza_vertical: float,
    fuerza_actuante: float,
    ancho_base: float,
    phi_base: float,
    cohesion_base: float,
    k1: float = 0.67,
    k2: float = 0.67,
    empuje_pasivo: float = 0.0,
    fs_requerido: float = 1.5,
) -> dict[str, Any]:
    """Calcula la resistencia por fricción, adhesión y pasivo opcional."""
    vertical = _numero("fuerza_vertical", fuerza_vertical, 0.0)
    horizontal = _numero("fuerza_actuante", fuerza_actuante, 0.0)
    base = _numero("ancho_base", ancho_base, 0.0)
    phi = _numero("phi_base", phi_base, 0.0)
    cohesion = _numero("cohesion_base", cohesion_base, 0.0)
    factor_phi = _numero("k1", k1, 0.0)
    factor_c = _numero("k2", k2, 0.0)
    pasivo = _numero("empuje_pasivo", empuje_pasivo, 0.0)
    fs_req = _numero("fs_deslizamiento_requerido", fs_requerido, 0.0)

    friccion = vertical * math.tan(math.radians(factor_phi * phi))
    adhesion = base * factor_c * cohesion
    resistencia = friccion + adhesion + pasivo
    fs = math.inf if horizontal <= TOLERANCIA else resistencia / horizontal
    resistencia_requerida = fs_req * horizontal

    return {
        "friccion": friccion,
        "adhesion": adhesion,
        "empuje_pasivo": pasivo,
        "resistencia_total": resistencia,
        "fuerza_actuante": horizontal,
        "fs": fs,
        "fs_requerido": fs_req,
        "cumple": fs >= fs_req,
        "deficit_resistencia": max(0.0, resistencia_requerida - resistencia),
    }


def calcular_presiones_base(
    fuerza_vertical: float,
    momento_resistente: float,
    momento_actuante: float,
    ancho_base: float,
) -> dict[str, Any]:
    """Calcula resultante, excentricidad y presiones bajo la zapata.

    Una excentricidad positiva desplaza la resultante hacia la puntera. Por
    ello, dentro del tercio central, q_puntera es la presión mayor.
    """
    vertical = _numero("fuerza_vertical", fuerza_vertical, 0.0)
    mr = _numero("momento_resistente", momento_resistente, 0.0)
    ma = _numero("momento_actuante", momento_actuante, 0.0)
    base = _numero("ancho_base", ancho_base, 0.0)
    if vertical <= TOLERANCIA or base <= TOLERANCIA:
        raise ValueError("La fuerza vertical y el ancho de base deben ser mayores que cero.")

    momento_neto = mr - ma
    x_resultante = momento_neto / vertical
    excentricidad = base / 2.0 - x_resultante
    limite_tercio = base / 6.0
    dentro_base = abs(excentricidad) < base / 2.0
    dentro_tercio = abs(excentricidad) <= limite_tercio + TOLERANCIA

    if dentro_tercio:
        q_media = vertical / base
        q_puntera = q_media * (1.0 + 6.0 * excentricidad / base)
        q_talon = q_media * (1.0 - 6.0 * excentricidad / base)
        ancho_contacto = base
        estado = "Conforme: la resultante cae dentro del tercio central."
    elif dentro_base:
        # Contacto triangular. Su longitud es 3 veces la distancia desde la
        # resultante hasta el borde comprimido.
        distancia_borde = base / 2.0 - abs(excentricidad)
        ancho_contacto = 3.0 * distancia_borde
        presion_maxima = 2.0 * vertical / ancho_contacto
        if excentricidad > 0.0:
            q_puntera, q_talon = presion_maxima, 0.0
        else:
            q_puntera, q_talon = 0.0, presion_maxima
        estado = "No conforme: la resultante está fuera del tercio central."
    else:
        ancho_contacto = 0.0
        q_puntera = math.inf if excentricidad > 0.0 else 0.0
        q_talon = math.inf if excentricidad < 0.0 else 0.0
        estado = "No conforme: la resultante cae fuera de la base."

    return {
        "momento_neto": momento_neto,
        "x_resultante": x_resultante,
        "excentricidad": excentricidad,
        "limite_tercio": limite_tercio,
        "dentro_tercio": dentro_tercio,
        "dentro_base": dentro_base,
        "ancho_contacto": ancho_contacto,
        "q_puntera": q_puntera,
        "q_talon": q_talon,
        "q_max": max(q_puntera, q_talon),
        "q_min": min(q_puntera, q_talon),
        "estado": estado,
    }


def factores_capacidad_portante(phi_grados: float) -> dict[str, float]:
    """Factores de capacidad de carga usados en la ecuación de Meyerhof."""
    phi = _numero("phi_base", phi_grados, 0.0)
    if phi >= 90.0:
        raise ValueError("phi_base debe ser menor que 90 grados.")
    if phi <= TOLERANCIA:
        return {"Nc": 5.14, "Nq": 1.0, "Ngamma": 0.0}

    phi_rad = math.radians(phi)
    nq = math.exp(math.pi * math.tan(phi_rad)) * math.tan(
        math.radians(45.0) + phi_rad / 2.0
    ) ** 2
    nc = (nq - 1.0) / math.tan(phi_rad)
    ngamma = (nq - 1.0) * math.tan(1.4 * phi_rad)
    return {"Nc": nc, "Nq": nq, "Ngamma": ngamma}


def capacidad_portante_meyerhof(
    cohesion: float,
    phi: float,
    gamma_suelo: float,
    profundidad_desplante: float,
    ancho_efectivo: float,
    fuerza_horizontal: float,
    fuerza_vertical: float,
    q_max: float,
    fs_requerido: float = 3.0,
) -> dict[str, Any]:
    """Calcula q_ult y el FS de capacidad portante mediante Meyerhof.

    Se adoptan factores de forma iguales a 1.0, coherentes con una zapata
    corrida analizada por metro longitudinal.
    """
    c = _numero("cohesion", cohesion, 0.0)
    angulo = _numero("phi", phi, 0.0)
    gamma = _numero("gamma_suelo", gamma_suelo, 0.0)
    df = _numero("profundidad_desplante", profundidad_desplante, 0.0)
    be = _numero("ancho_efectivo", ancho_efectivo, 0.0)
    horizontal = _numero("fuerza_horizontal", fuerza_horizontal, 0.0)
    vertical = _numero("fuerza_vertical", fuerza_vertical, 0.0)
    presion = _numero("q_max", q_max, 0.0)
    fs_req = _numero("fs_capacidad_requerido", fs_requerido, 0.0)

    if be <= TOLERANCIA or vertical <= TOLERANCIA:
        return {
            "calculado": False,
            "q_ult": 0.0,
            "fs": 0.0,
            "fs_requerido": fs_req,
            "cumple": False,
            "motivo": "No existe un ancho efectivo de contacto válido.",
        }

    factores = factores_capacidad_portante(angulo)
    relacion = df / be
    fcd = 1.0 + 0.4 * relacion
    phi_rad = math.radians(angulo)
    fqd = 1.0 + 2.0 * math.tan(phi_rad) * (1.0 - math.sin(phi_rad)) ** 2 * relacion
    fgammad = 1.0

    psi = math.degrees(math.atan2(horizontal, vertical))
    fci = max(0.0, 1.0 - psi / 90.0) ** 2
    fqi = fci
    # Cuando phi=0, Ngamma=0 y este factor no aporta a q_ult.
    fgammai = 1.0 if angulo <= TOLERANCIA else max(0.0, 1.0 - psi / angulo) ** 2

    sobrecarga_desplante = gamma * df
    termino_cohesion = c * factores["Nc"] * fcd * fci
    termino_sobrecarga = sobrecarga_desplante * factores["Nq"] * fqd * fqi
    termino_gamma = (
        0.5 * gamma * be * factores["Ngamma"] * fgammad * fgammai
    )
    q_ult = termino_cohesion + termino_sobrecarga + termino_gamma
    fs = math.inf if presion <= TOLERANCIA else q_ult / presion

    return {
        "calculado": True,
        "Nc": factores["Nc"],
        "Nq": factores["Nq"],
        "Ngamma": factores["Ngamma"],
        "psi": psi,
        "B_efectivo": be,
        "Fcd": fcd,
        "Fqd": fqd,
        "Fgammad": fgammad,
        "Fci": fci,
        "Fqi": fqi,
        "Fgammai": fgammai,
        "q_sobrecarga": sobrecarga_desplante,
        "termino_cohesion": termino_cohesion,
        "termino_sobrecarga": termino_sobrecarga,
        "termino_gamma": termino_gamma,
        "q_ult": q_ult,
        "fs": fs,
        "fs_requerido": fs_req,
        "cumple": fs >= fs_req,
        "motivo": "",
    }


def generar_recomendaciones(
    volteo: dict[str, Any],
    deslizamiento: dict[str, Any],
    presiones: dict[str, Any],
    capacidad: Optional[dict[str, Any]],
) -> list[str]:
    """Genera recomendaciones después de cotejar todas las verificaciones."""
    recomendaciones = []
    if not volteo["cumple"]:
        recomendaciones.append(
            "Aumentar el momento resistente: ampliar preferentemente el talón, "
            "aumentar el peso estabilizante o revisar la geometría del muro."
        )
    if not deslizamiento["cumple"]:
        recomendaciones.append(
            "Aumentar la resistencia al deslizamiento. Evaluar mayor ancho/peso "
            "de base y, si el criterio del curso lo permite, empuje pasivo o un dentellón."
        )
    if not presiones["dentro_tercio"]:
        recomendaciones.append(
            "Redimensionar la base para que la resultante se ubique en el tercio central."
        )
    if capacidad is not None and not capacidad["cumple"]:
        recomendaciones.append(
            "Aumentar el área efectiva de apoyo o mejorar/reemplazar el terreno de "
            "cimentación para elevar la seguridad por capacidad portante."
        )
    if not recomendaciones:
        recomendaciones.append("El muro cumple las verificaciones evaluadas.")
    return recomendaciones


def generar_mensajes_e050(
    criterios: dict[str, Any],
    volteo: dict[str, Any],
    deslizamiento: dict[str, Any],
    capacidad: Optional[dict[str, Any]],
) -> dict[str, list[str]]:
    """Genera mensajes de cumplimiento y alertas para mostrar en la interfaz."""
    condicion = criterios["condicion"]
    mensajes = []
    advertencias = []

    verificaciones = (
        ("volteo", volteo),
        ("deslizamiento", deslizamiento),
    )
    for nombre, resultado in verificaciones:
        mensaje = (
            f"FS por {nombre} = {resultado['fs']:.2f}; mínimo E.050 = "
            f"{resultado['fs_requerido']:.2f} ({condicion})."
        )
        if resultado["cumple"]:
            mensajes.append("CUMPLE: " + mensaje)
        else:
            alerta = "NO CUMPLE: " + mensaje
            mensajes.append(alerta)
            advertencias.append(alerta)

    if capacidad is None:
        mensajes.append(
            "PENDIENTE: no se evaluó capacidad portante porque faltan "
            "gamma_suelo_base y profundidad_desplante."
        )
    else:
        mensaje = (
            f"FS por capacidad portante = {capacidad['fs']:.2f}; mínimo "
            f"E.050 = {capacidad['fs_requerido']:.2f} ({condicion})."
        )
        if capacidad["cumple"]:
            mensajes.append("CUMPLE: " + mensaje)
        else:
            alerta = "NO CUMPLE: " + mensaje
            mensajes.append(alerta)
            advertencias.append(alerta)

    # El cálculo de estabilidad global requiere el conjunto muro-talud y una
    # superficie potencial de falla; no debe confundirse con estas revisiones.
    mensajes.append(
        "NOTA: la estabilidad global del conjunto muro-talud no es evaluada "
        "por este módulo."
    )
    return {"mensajes": mensajes, "advertencias": advertencias}


def evaluar_estabilidad(
    empuje_horizontal: float,
    momento_empuje: float,
    fuerzas_verticales: Iterable[Any],
    ancho_base: float,
    suelo_base: Any,
    *,
    condicion: str = "estatica",
    fs_volteo_requerido: Optional[float] = None,
    fs_deslizamiento_requerido: Optional[float] = None,
    fs_capacidad_requerido: Optional[float] = None,
    empuje_pasivo: float = 0.0,
    gamma_suelo_base: Optional[float] = None,
    profundidad_desplante: Optional[float] = None,
) -> dict[str, Any]:
    """Ejecuta todas las verificaciones y devuelve un resultado integrado.

    ``gamma_suelo_base`` y ``profundidad_desplante`` son opcionales. Mientras
    no estén disponibles en la interfaz, se calculan volteo, deslizamiento y
    presiones, pero la capacidad portante se informa como pendiente.
    """
    horizontal = _numero("empuje_horizontal", empuje_horizontal, 0.0)
    momento = _numero("momento_empuje", momento_empuje, 0.0)
    base = _numero("ancho_base", ancho_base, 0.0)
    if base <= TOLERANCIA:
        raise ValueError("ancho_base debe ser mayor que cero.")

    phi = _numero("phi_base", _campo(suelo_base, "phi_base"), 0.0)
    cohesion = _numero("c_base", _campo(suelo_base, "c_base"), 0.0)
    k1 = _numero("k1", _campo(suelo_base, "k1", 0.67), 0.0)
    k2 = _numero("k2", _campo(suelo_base, "k2", 0.67), 0.0)

    criterios = criterios_norma_e050(condicion)
    fs_volteo_aplicable = _criterio_aplicable(
        "fs_volteo_requerido", fs_volteo_requerido, criterios["fs_volteo"]
    )
    fs_deslizamiento_aplicable = _criterio_aplicable(
        "fs_deslizamiento_requerido", fs_deslizamiento_requerido,
        criterios["fs_deslizamiento"],
    )
    fs_capacidad_aplicable = _criterio_aplicable(
        "fs_capacidad_requerido", fs_capacidad_requerido,
        criterios["fs_capacidad"],
    )

    sumatorias = calcular_sumatorias(fuerzas_verticales)
    volteo = verificar_volteo(
        sumatorias["momento_resistente"], momento, fs_volteo_aplicable
    )
    deslizamiento = verificar_deslizamiento(
        sumatorias["peso_total"], horizontal, base, phi, cohesion,
        k1, k2, empuje_pasivo, fs_deslizamiento_aplicable,
    )
    presiones = calcular_presiones_base(
        sumatorias["peso_total"], sumatorias["momento_resistente"], momento, base
    )

    capacidad = None
    if gamma_suelo_base is not None and profundidad_desplante is not None:
        ancho_efectivo = max(0.0, base - 2.0 * abs(presiones["excentricidad"]))
        capacidad = capacidad_portante_meyerhof(
            cohesion, phi, gamma_suelo_base, profundidad_desplante,
            ancho_efectivo, horizontal, sumatorias["peso_total"],
            presiones["q_max"], fs_capacidad_aplicable,
        )

    mensajes_e050 = generar_mensajes_e050(
        criterios, volteo, deslizamiento, capacidad
    )
    recomendaciones = generar_recomendaciones(
        volteo, deslizamiento, presiones, capacidad
    )
    verificaciones_obligatorias = [
        volteo["cumple"], deslizamiento["cumple"], presiones["dentro_tercio"]
    ]
    if capacidad is not None:
        verificaciones_obligatorias.append(capacidad["cumple"])
    cumple_global = all(verificaciones_obligatorias)

    if mensajes_e050["advertencias"]:
        fallas = []
        if not volteo["cumple"]:
            fallas.append("volteo")
        if not deslizamiento["cumple"]:
            fallas.append("deslizamiento")
        if capacidad is not None and not capacidad["cumple"]:
            fallas.append("capacidad portante")
        estado = "NO CUMPLE E.050: " + ", ".join(fallas) + "."
    elif capacidad is None:
        estado = (
            "CUMPLE E.050 en volteo y deslizamiento; capacidad portante pendiente."
        )
    else:
        estado = "CUMPLE E.050" if cumple_global else "NO CUMPLE E.050"

    # Las primeras claves mantienen compatibilidad con interfaz.py V.2.0.
    return {
        "fs_volteo": volteo["fs"],
        "fs_deslizamiento": deslizamiento["fs"],
        "excentricidad": presiones["excentricidad"],
        "limite_tercio": presiones["limite_tercio"],
        "q_max": presiones["q_max"],
        "q_min": presiones["q_min"],
        "estado": estado,
        "sumatoria_vertical": sumatorias["peso_total"],
        "momento_resistente": sumatorias["momento_resistente"],
        # Resultados ampliados para futuras versiones de interfaz/exportación.
        "momento_actuante": momento,
        "q_puntera": presiones["q_puntera"],
        "q_talon": presiones["q_talon"],
        "x_resultante": presiones["x_resultante"],
        "momento_neto": presiones["momento_neto"],
        "dentro_tercio": presiones["dentro_tercio"],
        "ancho_contacto": presiones["ancho_contacto"],
        "fs_capacidad": None if capacidad is None else capacidad["fs"],
        "q_ult": None if capacidad is None else capacidad["q_ult"],
        "cumple": cumple_global,
        "condicion": criterios["condicion"],
        "criterios_e050": criterios,
        "mensajes_e050": mensajes_e050["mensajes"],
        "advertencias": mensajes_e050["advertencias"],
        "volteo": volteo,
        "deslizamiento": deslizamiento,
        "presiones": presiones,
        "capacidad_portante": capacidad,
        "cargas_verticales": sumatorias["detalle"],
        "recomendaciones": recomendaciones,
    }


__all__ = [
    "criterios_norma_e050",
    "calcular_cargas_geometricas",
    "calcular_sumatorias",
    "verificar_volteo",
    "verificar_deslizamiento",
    "calcular_presiones_base",
    "factores_capacidad_portante",
    "capacidad_portante_meyerhof",
    "generar_recomendaciones",
    "generar_mensajes_e050",
    "evaluar_estabilidad",
]
