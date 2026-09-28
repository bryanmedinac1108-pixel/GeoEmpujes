"""
Módulo de Cálculo Geotécnico.
Aplica teorías de Rankine/Coulomb e integra los esfuerzos para hallar fuerzas y momentos.
"""
import math
from modelos import Caso, Resultado, FilaResultado

def calcular_K(phi, alpha, beta, delta, condicion, metodo):
    """
    Calcula el coeficiente de empuje de tierras (Ka, Kp o K0).
    Convierte grados a radianes para usar las funciones trigonométricas de Python (math).
    """
    phi_rad = math.radians(phi)
    alpha_rad = math.radians(alpha)
    beta_rad = math.radians(beta)
    delta_rad = math.radians(delta)

    # Coeficiente en REPOSO (Fórmula empírica de Jaky)
    if condicion == 'reposo':
        return 1 - math.sin(phi_rad)

    # Método de RANKINE (Asume fricción suelo-muro delta = 0 y muro vertical beta = 90)
    if metodo == 'Rankine':
        cos_alpha = math.cos(alpha_rad)
        raiz = math.sqrt(abs(math.cos(alpha_rad)**2 - math.cos(phi_rad)**2))
        if condicion == 'activa':
            return cos_alpha * ((cos_alpha - raiz) / (cos_alpha + raiz))
        else: # pasiva
            return cos_alpha * ((cos_alpha + raiz) / (cos_alpha - raiz))

    # Método de COULOMB (Considera fricción delta y ángulos de muro beta)
    if metodo == 'Coulomb':
        sen_beta = math.sin(beta_rad)
        if condicion == 'activa':
            num = math.sin(beta_rad + phi_rad)**2
            den1 = sen_beta**2 * math.sin(beta_rad - delta_rad)
            den2 = (1 + math.sqrt( (math.sin(phi_rad + delta_rad)*math.sin(phi_rad - alpha_rad)) / 
                                   (math.sin(beta_rad - delta_rad)*math.sin(beta_rad + alpha_rad)) ))**2
            return num / (den1 * den2) if den1*den2 != 0 else 0
        else: # pasiva
            num = math.sin(beta_rad - phi_rad)**2
            den1 = sen_beta**2 * math.sin(beta_rad + delta_rad)
            den2 = (1 - math.sqrt( (math.sin(phi_rad + delta_rad)*math.sin(phi_rad + alpha_rad)) / 
                                   (math.sin(beta_rad + delta_rad)*math.sin(beta_rad + alpha_rad)) ))**2
            return num / (den1 * den2) if den1*den2 != 0 else 0
            
    return 0.0

def resolver(caso: Caso) -> Resultado:
    """
    Función principal que ejecuta el cálculo paso a paso.
    Discretiza el muro en pequeñas rebanadas (dz) para integrar numéricamente los esfuerzos.
    """
    filas = []
    H = caso.altura
    
    # 1. Definir la precisión del cálculo (paso dz = 1 milímetro para alta precisión)
    dz = 0.001 
    puntos_z = [i * dz for i in range(int(H / dz) + 1)]
    if puntos_z[-1] < H:
        puntos_z.append(H)

    # Variables acumuladoras a lo largo de la profundidad
    sigma_v = 0.0 
    z_anterior = 0.0
    
    # Listas para guardar los esfuerzos horizontales y luego calcular sus áreas (fuerzas)
    esf_suelo, esf_agua, esf_carga, esf_sismo = [], [], [], []
    zs = []

    # 2. Bucle principal: Recorrer cada punto 'z' desde la corona hasta la base
    for z in puntos_z:
        # Encontrar en qué estrato estamos parados
        z_acumulado = 0.0
        estrato_actual = caso.estratos[-1]
        num_est = len(caso.estratos)
        
        for i, est in enumerate(caso.estratos):
            z_acumulado += est.h
            if z <= z_acumulado + 1e-5: # Si z está dentro de este estrato
                estrato_actual = est
                num_est = i + 1
                break
                
        # 3. Lógica del Nivel Freático (Agua)
        es_saturado = caso.z_agua is not None and z > caso.z_agua
        gamma_usar = estrato_actual.gamma_sat if es_saturado else estrato_actual.gamma
        
        # Calcular esfuerzo efectivo vertical (σ'v)
        delta_z = z - z_anterior
        if es_saturado and caso.z_agua is not None and z_anterior < caso.z_agua:
            # Si el incremento cruza el nivel freático, calcular parte seca y parte húmeda
            dz_seco = caso.z_agua - z_anterior
            dz_sat = z - caso.z_agua
            sigma_v += (dz_seco * estrato_actual.gamma) + (dz_sat * (estrato_actual.gamma_sat - caso.gamma_agua))
        else:
            # Todo el incremento está seco o todo está saturado
            gamma_efectivo = (estrato_actual.gamma_sat - caso.gamma_agua) if es_saturado else estrato_actual.gamma
            sigma_v += delta_z * gamma_efectivo

        # 4. Calcular el coeficiente K para el estrato actual
        K = calcular_K(estrato_actual.phi, caso.alpha, caso.beta, estrato_actual.delta, caso.condicion, caso.metodo)
        
        # 5. Calcular Esfuerzo Horizontal del Suelo (σ'h = K * σ'v - 2c√K)
        raiz_K = math.sqrt(K) if K > 0 else 0
        p_suelo = (K * sigma_v)
        
        # Restar efecto de la cohesión (empuje activo) o sumar (empuje pasivo)
        if caso.condicion == 'activa':
            p_suelo -= 2 * estrato_actual.cohesion * raiz_K
            p_suelo = max(0, p_suelo) # Truncar a cero las grietas de tracción
        elif caso.condicion == 'pasiva':
            p_suelo += 2 * estrato_actual.cohesion * raiz_K

        # 6. Presión de poros (Agua)
        p_agua = (z - caso.z_agua) * caso.gamma_agua if es_saturado else 0.0
        
        # 7. Sobrecargas (Simplificación de Boussinesq)
        p_carga = 0.0
        for c in caso.cargas:
            if c.tipo.lower() in ['uniforme', 'franja']:
                p_carga += c.magnitud * K # La sobrecarga rectangular también se ve afectada por K

        # 8. Incremento Sísmico (Mononobe-Okabe simplificado)
        p_sismo = 0.0
        if caso.kh > 0 and caso.condicion == 'activa':
            # Pseudo-estático: Incremento triangular invertido simplificado
            delta_Kae = (0.75 * caso.kh) # Aproximación de Seed & Whitman
            p_sismo = delta_Kae * gamma_usar * z

        # Guardar valores para la tabla de resultados
        p_total = p_suelo + p_agua + p_carga + p_sismo
        filas.append(FilaResultado(z, num_est, sigma_v, K, p_suelo, p_agua, p_carga, p_sismo, p_total))
        
        # Almacenar en listas para integración
        zs.append(z); esf_suelo.append(p_suelo); esf_agua.append(p_agua)
        esf_carga.append(p_carga); esf_sismo.append(p_sismo)
        
        z_anterior = z

    # 9. INTEGRACIÓN (Fuerza = Área bajo la curva; Momento = Área * Brazo)
    def integrar(presiones, profundidades):
        F = 0.0
        M_corona = 0.0
        for i in range(len(profundidades)-1):
            z1, z2 = profundidades[i], profundidades[i+1]
            p1, p2 = presiones[i], presiones[i+1]
            h = z2 - z1
            
            # Área del trapecio (Fuerza del diferencial)
            dF = (p1 + p2) * h / 2.0
            
            # Centroide del trapecio respecto a la corona (z)
            if (p1 + p2) == 0:
                zc = z1 + h/2
            else:
                zc = z1 + h * (2*p2 + p1) / (3*(p1 + p2))
                
            F += dF
            M_corona += dF * zc
            
        # Momento respecto a la base: M_base = Fuerza * (H - z_centroide_global)
        y_barra = (H - (M_corona / F)) if F > 1e-9 else 0.0
        M_base = F * y_barra
        return F, M_base, y_barra

    P_s, M_s, y_s = integrar(esf_suelo, zs)
    P_w, M_w, y_w = integrar(esf_agua, zs)
    P_c, M_c, y_c = integrar(esf_carga, zs)
    P_e, M_e, y_e = integrar(esf_sismo, zs)

    # Sumatoria total
    P_tot = P_s + P_w + P_c + P_e
    M_tot = M_s + M_w + M_c + M_e
    y_tot = (M_tot / P_tot) if P_tot > 1e-9 else 0.0

    comp = {
        'Suelo': (P_s, M_s, y_s),
        'Agua': (P_w, M_w, y_w),
        'Sobrecarga': (P_c, M_c, y_c),
        'Incremento sísmico': (P_e, M_e, y_e)
    }

    # 10. Empaquetar todo en el objeto Resultado y retornarlo a la interfaz
    return Resultado(
        caso=caso, filas=filas, total=P_tot, momento=M_tot, y=y_tot, 
        componentes=comp, notas=["Cálculo completado exitosamente con discretización fina (dz=1mm)."]
    )