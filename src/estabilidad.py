"""
Módulo de Estabilidad de Muros (UNIDAD 2).
[V.2.0] Toma los resultados del empuje de tierras y evalúa si el muro resiste
o si falla por Volteo, Deslizamiento o Capacidad de Carga.
"""
# [V.2.0] Importa matemáticas para la trigonometría (fricción en la base)
import math

# [V.2.0] Función que verifica todos los estados límite de servicio y rotura
def evaluar_estabilidad(empuje_horizontal, momento_empuje, fuerzas_verticales, ancho_base, suelo_base):
    # [V.2.0] Recibe el Empuje Activo total calculado por el motor de la Unidad 1
    # [V.2.0] Recibe el Momento de Volteo (Actuante)
    # [V.2.0] Recibe un arreglo de CargasVerticales (Bloques de concreto/suelo estabilizante)
    # [V.2.0] Recibe la dimensión horizontal "B" de la base
    # [V.2.0] Recibe el objeto SueloCimentacion con la fricción y cohesión base
    
    # ---------------------------------------------------------
    # [V.2.0] 1. SUMATORIA DE FUERZAS Y MOMENTOS RESISTENTES
    # ---------------------------------------------------------
    # [V.2.0] Inicializa la sumatoria de fuerzas verticales (V)
    peso_total = 0.0
    # [V.2.0] Inicializa la sumatoria de momentos estabilizantes (M_R)
    momento_resistente = 0.0
    
    # [V.2.0] Recorre cada bloque estabilizante ingresado
    for fuerza in fuerzas_verticales:
        # [V.2.0] Suma su peso al total
        peso_total += fuerza.peso
        # [V.2.0] Suma su momento multiplicando Peso * Brazo (medido desde la punta)
        momento_resistente += fuerza.peso * fuerza.brazo_x
        
    # ---------------------------------------------------------
    # [V.2.0] 2. VERIFICACIÓN POR VOLTEO (VUELCO)
    # ---------------------------------------------------------
    # [V.2.0] Si existe tierra empujando, calcula el Factor de Seguridad
    if momento_empuje > 0:
        # [V.2.0] FS = Momento Resistente / Momento Actuante
        fs_volteo = momento_resistente / momento_empuje
    else:
        # [V.2.0] Si no hay empuje, el muro es infinitamente seguro al volteo
        fs_volteo = 999.0 
        
    # ---------------------------------------------------------
    # [V.2.0] 3. VERIFICACIÓN POR DESLIZAMIENTO
    # ---------------------------------------------------------
    # [V.2.0] Pasa el ángulo phi a radianes
    phi_rad = math.radians(suelo_base.phi_base)
    
    # [V.2.0] Calcula la Fricción pura: V * tan(k1 * phi)
    fuerza_friccion = peso_total * math.tan(suelo_base.k1 * phi_rad)
    
    # [V.2.0] Calcula la Adhesión de la base: Base * k2 * cohesión
    fuerza_adhesion = ancho_base * (suelo_base.k2 * suelo_base.c_base)
    
    # [V.2.0] Resistencia Total Horizontal (Omitiendo el empuje Pasivo Pp a favor de la seguridad)
    fuerza_resistente_total = fuerza_friccion + fuerza_adhesion
    
    # [V.2.0] Si existe empuje horizontal actuante, halla su FS
    if empuje_horizontal > 0:
        # [V.2.0] FS = Fuerzas Retenedoras / Fuerzas Deslizantes
        fs_deslizamiento = fuerza_resistente_total / empuje_horizontal
    else:
        # [V.2.0] Sin empuje, no hay deslizamiento
        fs_deslizamiento = 999.0
        
    # ---------------------------------------------------------
    # [V.2.0] 4. PRESIONES DE CONTACTO (CAPACIDAD DE CARGA)
    # ---------------------------------------------------------
    # [V.2.0] Sumatoria de Momentos Netos en la base
    momento_neto = momento_resistente - momento_empuje
    
    # [V.2.0] Ubicación de la Resultante Total medida desde la punta de la zapata (X barra)
    x_barra = momento_neto / peso_total if peso_total > 0 else 0.0
    
    # [V.2.0] Excentricidad de la resultante medida desde el centro exacto de la zapata (B/2)
    excentricidad = (ancho_base / 2.0) - x_barra
    
    # [V.2.0] Inicializa las presiones de esquina
    q_max, q_min = 0.0, 0.0
    estado_presiones = ""
    
    # [V.2.0] Solo calcula presiones si hay un muro pesado existiendo
    if peso_total > 0:
        # [V.2.0] Define el límite del Tercio Central (B/6)
        limite_tercio = ancho_base / 6.0
        
        # [V.2.0] Presión axial plana teórica (V/B)
        q_base = peso_total / ancho_base
        # [V.2.0] Componente de esfuerzo por flexión debido a la excentricidad (6e/B)
        factor_excentricidad = (6.0 * excentricidad) / ancho_base
        
        # [V.2.0] Si la excentricidad es menor al tercio central (Suelo 100% en compresión)
        if abs(excentricidad) <= limite_tercio:
            # [V.2.0] q = V/B (1 +/- 6e/B)
            q_max = q_base * (1.0 + abs(factor_excentricidad))
            q_min = q_base * (1.0 - abs(factor_excentricidad))
            # [V.2.0] Mensaje de estado normativo positivo
            estado_presiones = "Conforme (Cae en el tercio central, toda la base está en compresión)"
            
        # [V.2.0] Si sale del tercio central (El talón entra en tracción y se despega del suelo)
        else:
            # [V.2.0] Recalcula la presión máxima asumiendo un diagrama triangular comprimido acortado
            q_max = (4.0 * peso_total) / (3.0 * (ancho_base - 2.0 * abs(excentricidad)))
            # [V.2.0] La presión mínima es cero porque el suelo no puede jalar el concreto hacia abajo
            q_min = 0.0 
            # [V.2.0] Mensaje de alerta por riesgo de desprendimiento
            estado_presiones = "¡Alerta! Excentricidad fuera del tercio central (El talón se levanta)"
            
    # [V.2.0] Devuelve los resultados empaquetados en un Diccionario para la interfaz
    return {
        "fs_volteo": fs_volteo,
        "fs_deslizamiento": fs_deslizamiento,
        "excentricidad": excentricidad,
        "limite_tercio": ancho_base / 6.0,
        "q_max": q_max,
        "q_min": q_min,
        "estado": estado_presiones,
        "sumatoria_vertical": peso_total,
        "momento_resistente": momento_resistente
    }