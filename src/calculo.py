"""
Módulo de Cálculo Geotécnico.
[V.1.0] Aplica estrictamente las fórmulas del curso para Empujes de Tierras:
- Coulomb / Rankine para K estático.
- Mononobe-Okabe para K dinámico (Sismo).
- Jarquio (1981) para fuerzas de sobrecargas de franja finita.
- Ecuaciones de Elasticidad para cargas puntuales y lineales.
- Integración matemática analítica y numérica de esfuerzos.
"""
# [V.1.0] Importa el módulo matemático estándar de Python para funciones trigonométricas y raíces cuadradas.
import math
# [V.1.0] Importa las clases de estructuras de datos definidas en el archivo modelos.py.
from modelos import Caso, Resultado, FilaResultado, AreaDetalle

# [V.1.0] Función para calcular el coeficiente de empuje de tierras estático (Ka, Kp o K0).
def calcular_K_estatico(phi, alpha, beta, delta, condicion, metodo):
    # [V.1.0] Convierte todos los ángulos de entrada (grados) a radianes para usarlos en math.sin/cos.
    phi_r, alpha_r, beta_r, delta_r = map(math.radians, [phi, alpha, beta, delta])
    
    # [V.1.0] Si la condición solicitada es empuje en reposo.
    if condicion == 'reposo':
        # [V.1.0] Aplica la fórmula empírica de Jaky (1 - sen(φ)).
        return 1.0 - math.sin(phi_r)
        
    # [V.1.0] Si el método seleccionado es la teoría de Rankine (superficie de falla plana, sin fricción muro-suelo).
    if metodo == 'Rankine':
        # [V.1.0] Calcula el coseno del ángulo de inclinación del relleno.
        cos_a = math.cos(alpha_r)
        # [V.1.0] Calcula la raíz cuadrada de la ecuación de Rankine (usa valor absoluto para evitar errores de dominio).
        raiz = math.sqrt(abs(math.cos(alpha_r)**2 - math.cos(phi_r)**2))
        # [V.1.0] Si la condición es activa (el muro cede).
        if condicion == 'activa':
            # [V.1.0] Retorna el coeficiente Ka de Rankine.
            return cos_a * ((cos_a - raiz) / (cos_a + raiz))
        # [V.1.0] Si la condición es pasiva (el muro empuja al suelo).
        else:
            # [V.1.0] Retorna el coeficiente Kp de Rankine.
            return cos_a * ((cos_a + raiz) / (cos_a - raiz))
            
    # [V.1.0] Si el método seleccionado es la teoría de Coulomb (considera fricción muro-suelo y ángulo del muro).
    if metodo == 'Coulomb':
        # [V.1.0] Calcula el seno del ángulo de inclinación del respaldo del muro.
        sen_b = math.sin(beta_r)
        # [V.1.0] Si la condición es activa.
        if condicion == 'activa':
            # [V.1.0] Calcula el numerador de la fórmula de Coulomb activo.
            num = math.sin(beta_r + phi_r)**2
            # [V.1.0] Calcula la primera parte del denominador.
            den1 = sen_b**2 * math.sin(beta_r - delta_r)
            # [V.1.0] Calcula el término dentro de la raíz cuadrada en el denominador.
            val_raiz = (math.sin(phi_r + delta_r)*math.sin(phi_r - alpha_r))/(math.sin(beta_r - delta_r)*math.sin(alpha_r + beta_r))
            # [V.1.0] Previene números imaginarios forzando a cero si el valor es negativo (límite físico).
            if val_raiz < 0: val_raiz = 0
            # [V.1.0] Calcula la segunda parte del denominador (el término entre corchetes al cuadrado).
            den2 = (1.0 + math.sqrt(val_raiz))**2
            # [V.1.0] Retorna Ka de Coulomb, evitando división por cero.
            return num / (den1 * den2) if den1*den2 != 0 else 0.0
        # [V.1.0] Si la condición es pasiva.
        else: 
            # [V.1.0] Calcula el numerador de la fórmula de Coulomb pasivo.
            num = math.sin(beta_r - phi_r)**2
            # [V.1.0] Calcula la primera parte del denominador.
            den1 = sen_b**2 * math.sin(beta_r + delta_r)
            # [V.1.0] Calcula el término dentro de la raíz para el caso pasivo.
            val_raiz = (math.sin(phi_r + delta_r)*math.sin(phi_r + alpha_r))/(math.sin(beta_r + delta_r)*math.sin(alpha_r + beta_r))
            # [V.1.0] Previene números imaginarios.
            if val_raiz < 0: val_raiz = 0
            # [V.1.0] Calcula la segunda parte del denominador.
            den2 = (1.0 - math.sqrt(val_raiz))**2
            # [V.1.0] Retorna Kp de Coulomb, evitando división por cero.
            return num / (den1 * den2) if den1*den2 != 0 else 0.0
    # [V.1.0] Retorno de seguridad por si no entra en ningún condicional.
    return 0.0

# [V.1.0] Función para calcular el coeficiente de empuje dinámico/sísmico usando el método de Mononobe-Okabe.
def calcular_K_dinamico(phi, alpha, beta, delta, kh, kv):
    # [V.1.0] Si no hay aceleraciones sísmicas, el coeficiente dinámico adicional es cero.
    if kh == 0 and kv == 0: return 0.0
    # [V.1.0] Calcula el ángulo de inercia sísmica (theta) usando los coeficientes horizontal y vertical.
    theta_r = math.atan(kh / (1.0 - kv))
    # [V.1.0] Convierte los ángulos geométricos a radianes.
    phi_r, alpha_r, beta_r, delta_r = map(math.radians, [phi, alpha, beta, delta])
    
    # [V.1.0] Numerador de la ecuación de Mononobe-Okabe.
    num = math.sin(beta_r + phi_r - theta_r)**2
    # [V.1.0] Primera parte del denominador.
    den1 = math.cos(theta_r) * math.sin(beta_r)**2 * math.sin(beta_r - delta_r - theta_r)
    # [V.1.0] Término interno de la raíz cuadrada en el denominador.
    val_raiz = (math.sin(phi_r + delta_r)*math.sin(phi_r - alpha_r - theta_r))/(math.sin(beta_r - delta_r - theta_r)*math.sin(alpha_r + beta_r))
    # [V.1.0] Restricción física para evitar raíces de números negativos.
    if val_raiz < 0: val_raiz = 0 
    # [V.1.0] Segunda parte del denominador.
    den2 = (1.0 + math.sqrt(val_raiz))**2
    # [V.1.0] Retorna el coeficiente Kae, previniendo división por cero.
    return num / (den1 * den2) if den1*den2 != 0 else 0.0

# [V.1.0] Función para calcular el esfuerzo horizontal de una sobrecarga de franja según Boussinesq modificado.
def boussinesq_franja(q, a_p, b_p, z):
    # [V.1.0] En la superficie (z=0) el esfuerzo lateral por Boussinesq es cero.
    if z <= 0: return 0.0
    # [V.1.0] Calcula el ángulo beta en radianes (ángulo subtendido por el ancho de la franja desde la profundidad z).
    beta_rad = math.atan((a_p + b_p)/z) - math.atan(a_p/z)
    # [V.1.0] Calcula el ángulo alpha en radianes (orientación geométrica hacia la franja).
    alpha_rad = math.atan(z/(a_p + b_p))
    # [V.1.0] Retorna la presión horizontal evaluada en esa profundidad z.
    return (2.0 * q / math.pi) * (beta_rad - math.sin(beta_rad)*math.cos(2.0*alpha_rad))

# [V.1.0] Función principal que orquesta todos los cálculos del perfil del muro.
def resolver(caso: Caso) -> Resultado:
    # [V.1.0] Inicializa la lista que guardará los resultados punto por punto.
    filas = []
    # [V.1.0] Obtiene la altura total del muro desde el objeto caso.
    H = caso.altura
    # [V.1.0] Define el tamaño de paso diferencial (5 milímetros) para la integración numérica.
    dz = 0.005 
    # [V.1.0] Genera un arreglo de profundidades (z) desde 0 hasta H en intervalos de dz.
    puntos_z = [i * dz for i in range(int(H / dz) + 1)]
    # [V.1.0] Asegura que el último punto evaluado sea exactamente la base del muro (H).
    if puntos_z[-1] < H: puntos_z.append(H)
    
    # [V.1.0] Inicializa variables acumuladoras para el esfuerzo vertical y el paso anterior.
    sigma_v = 0.0
    z_anterior = 0.0
    
    # [V.1.0] Listas para almacenar las presiones independientes por cada capa/tipo.
    esf_suelo, esf_agua, esf_sismo = [], [], []
    esf_c_unif, esf_c_3d = [], []

    # [V.1.0] Bucle principal: recorre cada milímetro de profundidad z.
    for z in puntos_z:
        # [V.1.0] Variables para identificar en qué estrato nos encontramos a esta profundidad z.
        z_acumulado, est_actual, num_est = 0.0, caso.estratos[-1], len(caso.estratos)
        # [V.1.0] Recorre los estratos definidos por el usuario.
        for i, est in enumerate(caso.estratos):
            # [V.1.0] Suma el espesor del estrato.
            z_acumulado += est.h 
            # [V.1.0] Si la profundidad actual z está dentro de este estrato (con un pequeño margen de tolerancia).
            if z <= z_acumulado + 1e-5: 
                # [V.1.0] Asigna el estrato actual y su número identificador, y rompe el bucle.
                est_actual = est; num_est = i + 1; break
                
        # [V.1.0] Determina si a esta profundidad el suelo está bajo el nivel freático.
        es_sat = caso.z_agua is not None and z > caso.z_agua
        # [V.1.0] Calcula el incremento de profundidad respecto a la iteración anterior.
        delta_z = z - z_anterior
        
        # [V.1.0] CÁLCULO DEL ESFUERZO VERTICAL EFECTIVO (sigma_v)
        # [V.1.0] Si el punto actual está bajo agua, pero el punto anterior estaba seco (transición exacta del NF).
        if es_sat and caso.z_agua is not None and z_anterior < caso.z_agua:
            # [V.1.0] Suma la porción seca con gamma natural, y la porción sumergida con gamma efectivo (sat - agua).
            sigma_v += ((caso.z_agua - z_anterior) * est_actual.gamma) + ((z - caso.z_agua) * (est_actual.gamma_sat - caso.gamma_agua))
        else:
            # [V.1.0] Suma el peso del segmento completo (efectivo si está bajo agua, natural si está seco).
            sigma_v += delta_z * ((est_actual.gamma_sat - caso.gamma_agua) if es_sat else est_actual.gamma)

        # [V.1.0] Calcula el coeficiente estático K para este estrato específico.
        Ka = calcular_K_estatico(est_actual.phi, caso.alpha, caso.beta, est_actual.delta, caso.condicion, caso.metodo)
        # [V.1.0] Extrae la raíz de Ka (asegurando que no sea negativa) para usarla en la fórmula de cohesión.
        raiz_K = math.sqrt(max(0, Ka))
        
        # [V.1.0] CÁLCULO DE LA PRESIÓN DEL SUELO
        # [V.1.0] Componente friccionante.
        p_suelo = (Ka * sigma_v) 
        # [V.1.0] Si es activa, la cohesión disminuye el empuje (puede generar tracción/valores negativos).
        if caso.condicion == 'activa': p_suelo = p_suelo - 2 * est_actual.cohesion * raiz_K
        # [V.1.0] Si es pasiva, la cohesión aumenta la resistencia del suelo.
        elif caso.condicion == 'pasiva': p_suelo += 2 * est_actual.cohesion * raiz_K

        # [V.1.0] CÁLCULO DE LA PRESIÓN DEL AGUA (Hidrostática pura).
        p_agua = (z - caso.z_agua) * caso.gamma_agua if es_sat else 0.0
        
        # [V.1.0] CÁLCULO DE SOBRECARGAS
        # [V.1.0] Suma todas las sobrecargas infinitas/uniformes multiplicadas por el coeficiente K.
        p_c_unif = sum(c.magnitud * Ka for c in caso.cargas if c.tipo.lower() == 'uniforme')
        # [V.1.0] Suma los bulbos de presión de las sobrecargas de franja evaluados en la profundidad z.
        p_c_fran = sum(boussinesq_franja(c.magnitud, c.a, c.b, z) for c in caso.cargas if c.tipo.lower() == 'franja')
        
        # [V.1.0] Inicializa variable para presiones de cargas 3D (puntuales y lineales).
        p_c_3d = 0.0
        # [V.1.0] Itera sobre todas las cargas para procesar puntuales y lineales.
        for c in caso.cargas:
            tipo = c.tipo.lower()
            if tipo in ['lineal', 'puntual']:
                # [V.1.0] m y n son parámetros adimensionales de las fórmulas de elasticidad.
                m = c.a / H if H > 0 else 0
                n = z / H if H > 0 else 0
                # [V.1.0] Evita división por cero en la superficie.
                if z > 0: 
                    if tipo == 'lineal': # [V.1.0] Fórmulas para carga lineal paralela al muro.
                        if m > 0.4:
                            den = (m*m + n*n)**2
                            if den > 1e-9: p_c_3d += (4.0 * c.magnitud / (math.pi * H)) * (m*m*n / den)
                        else: # [V.1.0] Ecuación experimental modificada para cargas muy cercanas al muro.
                            den = (0.16 + n*n)**2
                            p_c_3d += (c.magnitud / H) * (0.203 * n / den)
                    elif tipo == 'puntual': # [V.1.0] Fórmulas para carga puntual aislada.
                        if m > 0.4:
                            den = (m*m + n*n)**3
                            if den > 1e-9: p_c_3d += (1.77 * c.magnitud / (H*H)) * (m*m*n*n / den)
                        else:
                            den = (0.16 + n*n)**3
                            p_c_3d += (0.28 * c.magnitud / (H*H)) * (n*n / den)

        # [V.1.0] Totaliza todas las presiones por sobrecargas en esta profundidad z.
        p_carga_total = p_c_unif + p_c_fran + p_c_3d
        
        # [V.1.0] CÁLCULO SÍSMICO
        p_sismo = 0.0
        # [V.1.0] Solo se calcula si hay coeficiente sísmico horizontal y es condición activa.
        if caso.kh > 0 and caso.condicion == 'activa':
            # [V.1.0] Obtiene K dinámico de Mononobe-Okabe.
            Kae = calcular_K_dinamico(est_actual.phi, caso.alpha, caso.beta, est_actual.delta, caso.kh, caso.kv)
            # [V.1.0] Presión dinámica total (suelo + sismo).
            p_din_total = sigma_v * Kae 
            # [V.1.0] El empuje sísmico neto es el total dinámico menos la presión estática de suelo (ignorando tracciones).
            p_sismo = p_din_total - max(0, p_suelo)
            
        # [V.1.0] Sumatoria de la presión total lateral a la profundidad z.
        p_total = p_suelo + p_agua + p_carga_total + p_sismo
        # [V.1.0] Guarda la fila de resultados para formar la tabla matriz.
        filas.append(FilaResultado(z, num_est, sigma_v, Ka, p_suelo, p_agua, p_carga_total, p_sismo, p_total))
        
        # [V.1.0] Almacena en los arreglos paralelos para la posterior integración numérica.
        esf_suelo.append(p_suelo)
        esf_agua.append(p_agua)
        esf_sismo.append(p_sismo)
        esf_c_unif.append(p_c_unif)
        esf_c_3d.append(p_c_3d)
        
        # [V.1.0] Prepara la siguiente iteración.
        z_anterior = z

    # [V.1.0] Función interna para integrar vectores de presiones y encontrar Fuerza y Centroide.
    def integrar_arreglo(presiones):
        # [V.1.0] Fuerza total y Momento respecto a la base del muro.
        F, M_base = 0.0, 0.0 
        # [V.1.0] Bucle para integrar mediante el método del trapecio milímetro a milímetro.
        for i in range(len(puntos_z)-1):
            # [V.1.0] Profundidades del mini-segmento.
            z1, z2 = puntos_z[i], puntos_z[i+1] 
            # [V.1.0] Presiones del mini-segmento.
            p1, p2 = presiones[i], presiones[i+1] 
            # [V.1.0] Altura del diferencial.
            h_tr = z2 - z1 
            # [V.1.0] Área del trapecio (Diferencial de Fuerza).
            dF = (p1 + p2) * h_tr / 2.0 
            # [V.1.0] Centroide del trapecio respecto a la corona (superficie).
            zc = z1 + h_tr/2 if abs(p1 + p2) < 1e-9 else z1 + h_tr * (p1 + 2*p2) / (3*(p1 + p2))
            # [V.1.0] Acumula la fuerza.
            F += dF 
            # [V.1.0] Acumula el momento multiplicando fuerza por brazo desde la base.
            M_base += dF * (H - zc) 
        # [V.1.0] Calcula el brazo de palanca resultante (y barra) respecto a la base.
        y_b = M_base / F if abs(F) > 1e-9 else 0.0
        return F, M_base, y_b

    # [V.1.0] Integra los arreglos para obtener las fuerzas totales de suelo y agua.
    P_s, M_s, y_s = integrar_arreglo(esf_suelo)
    P_w, M_w, y_w = integrar_arreglo(esf_agua)
    
    # [V.1.0] Integra las sobrecargas uniformes y puntuales/lineales.
    P_c_unif, M_c_unif, _ = integrar_arreglo(esf_c_unif)
    P_c_3d, M_c_3d, _ = integrar_arreglo(esf_c_3d)
    
    # [V.1.0] CÁLCULO ANALÍTICO DE SOBRECARGA DE FRANJA (Jarquio, 1981)
    P_c_fran, M_c_fran = 0.0, 0.0
    for c in caso.cargas:
        if c.tipo.lower() == 'franja':
            # [V.1.0] Distancia al muro.
            b_prime = c.a 
            # [V.1.0] Ancho de la franja.
            a_prime = c.b 
            # [V.1.0] Ángulos en grados desde el fondo del muro hacia los límites de la carga en superficie.
            theta1 = math.degrees(math.atan(b_prime / H))
            theta2 = math.degrees(math.atan((a_prime + b_prime) / H))
            # [V.1.0] Si la franja tiene un ancho real y cae dentro de la zona de influencia geométrica.
            if (theta2 - theta1) > 0:
                # [V.1.0] Ecuación de fuerza analítica de Jarquio.
                P_q = (c.magnitud / 90.0) * (H * (theta2 - theta1))
                # [V.1.0] Cálculos intermedios para hallar el centro de aplicación exacto según Jarquio.
                R = ((a_prime + b_prime)**2) * (90.0 - theta2)
                Q = (b_prime**2) * (90.0 - theta1)
                num_y = (H**2)*(theta2 - theta1) + (R - Q) - 57.3 * a_prime * H
                # [V.1.0] Brazo de aplicación Yq.
                y_q = H - (num_y / (2.0 * H * (theta2 - theta1))) 
                # [V.1.0] Acumula resultados si hubiera más de una franja.
                P_c_fran += P_q
                M_c_fran += (P_q * y_q)
                
    # [V.1.0] Unifica las resultantes de todas las naturalezas de cargas.
    P_c_total = P_c_unif + P_c_fran + P_c_3d
    M_c_total = M_c_unif + M_c_fran + M_c_3d
    y_c_total = M_c_total / P_c_total if abs(P_c_total) > 1e-9 else 0.0

    # [V.1.0] ASIGNACIÓN DIRECTA DE LA FUERZA SÍSMICA NET
    P_sismo_neto, M_sismo_neto, y_sismo_neto = 0.0, 0.0, 0.0
    if caso.kh > 0 and caso.condicion == 'activa':
        # [V.1.0] Recalcula e integra la cuña dinámica completa usando Mononobe-Okabe.
        F_din, M_base_din = integrar_arreglo([f.sigma_v * calcular_K_dinamico(caso.estratos[f.estrato-1].phi, caso.alpha, caso.beta, caso.estratos[f.estrato-1].delta, caso.kh, caso.kv) for f in filas])[:2]
        # [V.1.0] El incremento sísmico neto es el dinámico total menos el estático del suelo.
        P_sismo_neto = F_din - P_s
        # [V.1.0] Regla teórica de Mononobe-Okabe: el incremento sísmico se aplica a 0.6H.
        y_sismo_neto = 0.6 * H 
        # [V.1.0] Calcula el momento producido por este incremento.
        M_sismo_neto = P_sismo_neto * y_sismo_neto

    # [V.1.0] SUMATORIA FINAL DEL MURO (Fuerzas y Momentos).
    P_tot = P_s + P_w + P_c_total + P_sismo_neto
    M_tot = M_s + M_w + M_c_total + M_sismo_neto
    # [V.1.0] Brazo de palanca final de toda la resultante sobre el muro.
    y_tot = (M_tot / P_tot) if abs(P_tot) > 1e-9 else 0.0
    
    # [V.1.0] Diccionario para enviar las componentes agrupadas a la interfaz gráfica.
    comp = {
        'Suelo': (P_s, M_s, y_s), 
        'Agua': (P_w, M_w, y_w), 
        'Sobrecarga': (P_c_total, M_c_total, y_c_total), 
        'Incremento sísmico': (P_sismo_neto, M_sismo_neto, y_sismo_neto)
    }

    # [V.1.0] SECCIÓN GEOMÉTRICA PARA LA MEMORIA DE CÁLCULO (CORTES EN RECTÁNGULOS Y TRIÁNGULOS)
    detalles = []
    area_idx = 1
    
    # [V.1.0] Función que subdivide un perfil de presiones en formas regulares identificables para graficar.
    def extraer_detalles_arr(presiones, nombre_comp, force_numerical=False):
        nonlocal area_idx
        chunks, chunk_z, chunk_p = [], [], []
        # [V.1.0] Evalúa si existe NF para partir la geometría en ese punto exacto.
        z_agua_eval = caso.z_agua if caso.z_agua is not None else 9999.0
        # [V.1.0] Etiqueta única por estrato y si está bajo agua o no.
        current_id = f"{filas[0].estrato}_{filas[0].z > z_agua_eval}"
        
        # [V.1.0] Agrupa los valores punto por punto separando por fronteras (estratos / nivel freático).
        for f, p_val in zip(filas, presiones):
            c_id = f"{f.estrato}_{f.z > z_agua_eval}"
            # [V.1.0] Si cambió de estrato o pasó por el nivel freático, guarda el bloque (chunk) y crea uno nuevo.
            if c_id != current_id:
                chunks.append((chunk_z, chunk_p)); chunk_z, chunk_p = [f.z], [p_val]
                current_id = c_id
            else:
                chunk_z.append(f.z); chunk_p.append(p_val)
        if chunk_z: chunks.append((chunk_z, chunk_p))
            
        # [V.1.0] Tolerancia numérica para considerar valores nulos y evitar errores de redondeo computacional.
        TOL = 0.1 
        new_chunks = []
        
        # [V.1.0] Interpolador para encontrar el punto exacto donde la presión cambia de negativo a positivo (Zc).
        for z_arr, p_arr in chunks:
            p_top, p_bot = p_arr[0], p_arr[-1]
            # [V.1.0] Si los signos son opuestos (hay tensión arriba y compresión abajo).
            if p_top * p_bot < -TOL: 
                h_tr = z_arr[-1] - z_arr[0]
                # [V.1.0] Por relación de triángulos, calcula la profundidad donde la presión es cero.
                z_zero = z_arr[0] + h_tr * abs(p_top) / (abs(p_top) + abs(p_bot))
                # [V.1.0] Corta el bloque en dos: la cuña negativa (arriba) y la cuña positiva (abajo).
                new_chunks.append(([z_arr[0], z_zero], [p_top, 0.0]))
                new_chunks.append(([z_zero, z_arr[-1]], [0.0, p_bot]))
            else:
                new_chunks.append((z_arr, p_arr))

        # [V.1.0] Itera sobre los bloques ya limpios y divididos para transformarlos en geometría básica.
        for z_arr, p_arr in new_chunks:
            # [V.1.0] Si toda la porción está vacía/tiene cero presión, la ignora.
            if all(abs(p) <= TOL for p in p_arr): continue
            z_top, z_bot = z_arr[0], z_arr[-1]
            p_top, p_bot = p_arr[0], p_arr[-1]
            h_tr = z_bot - z_top
            if h_tr <= 1e-9: continue
            
            # [V.1.0] Si la curva es compleja (por ej. puntual/lineal) y no forma líneas rectas, pide integrarla como un solo bloque sólido.
            if force_numerical:
                F_num, M_coro = 0.0, 0.0
                # [V.1.0] Realiza la integración matemática para dar el resultado al PDF.
                for i in range(len(z_arr)-1):
                    z1, z2 = z_arr[i], z_arr[i+1]
                    p1, p2 = p_arr[i], p_arr[i+1]
                    h = z2 - z1
                    dF = (p1 + p2) * h / 2.0
                    zc = z1 + h/2 if abs(p1+p2)<1e-9 else z1 + h*(p1+2*p2)/(3*(p1+p2))
                    F_num += dF
                    M_coro += dF * zc
                zc_total = M_coro / F_num if abs(F_num) > 1e-9 else z_top + h_tr/2
                y_base = H - zc_total
                max_p = max(abs(p) for p in p_arr)
                detalles.append(AreaDetalle(area_idx, nombre_comp, 'Integración numérica', F_num, zc_total, y_base, 0.0, max_p, h_tr))
                area_idx += 1
                continue
                
            # [V.1.0] Si la presión superior es 0 y la inferior no, es un Triángulo con base abajo.
            if abs(p_bot) > TOL and abs(p_top) <= TOL:
                F = (p_bot * h_tr) / 2.0
                detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', F, z_top + h_tr*(2/3), H - (z_top + h_tr*(2/3)), p_bot / 3.0, p_bot, h_tr))
                area_idx += 1
            # [V.1.0] Si la presión inferior es 0 y la superior no, es un Triángulo invertido con base arriba.
            elif abs(p_top) > TOL and abs(p_bot) <= TOL:
                F = (p_top * h_tr) / 2.0
                detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', F, z_top + h_tr*(1/3), H - (z_top + h_tr*(1/3)), p_top / 3.0, p_top, h_tr))
                area_idx += 1
            # [V.1.0] Si hay presión arriba y abajo (Trapecio), lo corta en un Rectángulo y un Triángulo.
            else:
                sign = 1 if p_top > 0 else -1
                # [V.1.0] Encuentra el valor más pequeño para usarlo como ancho del Rectángulo base.
                min_p_abs = min(abs(p_top), abs(p_bot))
                min_p = min_p_abs * sign
                F_rect = min_p * h_tr
                detalles.append(AreaDetalle(area_idx, nombre_comp, 'Rectángulo', F_rect, z_top + h_tr/2, H - (z_top + h_tr/2), min_p / 2.0, min_p, h_tr))
                area_idx += 1
                
                # [V.1.0] El resto de la presión (la diferencia) forma el Triángulo restante.
                if abs(p_bot - p_top) > TOL:
                    F_tri = (p_bot - p_top) * h_tr / 2.0
                    zc_tri = z_top + h_tr*(2/3) if abs(p_bot) > abs(p_top) else z_top + h_tr*(1/3)
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', F_tri, zc_tri, H - zc_tri, min_p + (p_bot - p_top)/3.0, (p_bot - p_top), h_tr))
                    area_idx += 1

    # [V.1.0] Llama a la función de extracción geométrica para cada una de las capas.
    extraer_detalles_arr(esf_suelo, 'Suelo')
    extraer_detalles_arr(esf_agua, 'Agua')
    
    # [V.1.0] Corta en rectángulos a las sobrecargas infinitas.
    if abs(P_c_unif) > 1e-5: extraer_detalles_arr(esf_c_unif, 'Sobrecarga')
    # [V.1.0] Extrae como bloque numérico curvo a las cargas tridimensionales (puntual/lineal).
    if abs(P_c_3d) > 1e-5: extraer_detalles_arr(esf_c_3d, 'Sobrecarga', force_numerical=True)
    
    # [V.1.0] Para el caso de la franja, añade al PDF la solución analítica de Jarquio pura sin cortarla.
    if abs(P_c_fran) > 1e-5:
        y_c_fran = M_c_fran / P_c_fran if abs(P_c_fran) > 1e-9 else 0.0
        # [V.1.0] Calcula la presión máxima de Boussinesq solo para propósitos estéticos en el gráfico.
        p_max_boussinesq = sum(boussinesq_franja(c.magnitud, c.a, c.b, H - y_c_fran) for c in caso.cargas if c.tipo.lower() == 'franja')
        detalles.append(AreaDetalle(area_idx, 'Sobrecarga', 'Solución de Jarquio', P_c_fran, H - y_c_fran, y_c_fran, p_max_boussinesq / 2.0, P_c_fran, H))
        area_idx += 1 
        
    # [V.1.0] Agrega el bloque de la cuña sísmica dinámica.
    if abs(P_sismo_neto) > 1e-5: extraer_detalles_arr(esf_sismo, 'Sismo')

    # [V.1.0] Retorna todos los arreglos, integrales y memorias listos para renderizar y exportar.
    return Resultado(caso=caso, filas=filas, total=P_tot, momento=M_tot, y=y_tot, componentes=comp, detalles=detalles, notas=["Cálculo actualizado con Ecuaciones de Elasticidad para cargas puntuales y lineales."])