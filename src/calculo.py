"""
Módulo de Cálculo Geotécnico.
Detecta vértices del diagrama y almacena las bases y alturas
de cada forma geométrica para el reporte PDF paso a paso.
"""
import math
from modelos import Caso, Resultado, FilaResultado, AreaDetalle

def calcular_K(phi, alpha, beta, delta, condicion, metodo):
    phi_rad, alpha_rad, beta_rad, delta_rad = map(math.radians, [phi, alpha, beta, delta])
    if condicion == 'reposo': return 1 - math.sin(phi_rad)
    if metodo == 'Rankine':
        cos_alpha = math.cos(alpha_rad)
        raiz = math.sqrt(abs(math.cos(alpha_rad)**2 - math.cos(phi_rad)**2))
        return cos_alpha * ((cos_alpha - raiz)/(cos_alpha + raiz)) if condicion == 'activa' else cos_alpha * ((cos_alpha + raiz)/(cos_alpha - raiz))
    if metodo == 'Coulomb':
        sen_beta = math.sin(beta_rad)
        if condicion == 'activa':
            num = math.sin(beta_rad + phi_rad)**2
            den1 = sen_beta**2 * math.sin(beta_rad - delta_rad)
            den2 = (1 + math.sqrt((math.sin(phi_rad + delta_rad)*math.sin(phi_rad - alpha_rad))/(math.sin(beta_rad - delta_rad)*math.sin(beta_rad + alpha_rad))))**2
            return num / (den1 * den2) if den1*den2 != 0 else 0
        else: 
            num = math.sin(beta_rad - phi_rad)**2
            den1 = sen_beta**2 * math.sin(beta_rad + delta_rad)
            den2 = (1 - math.sqrt((math.sin(phi_rad + delta_rad)*math.sin(phi_rad + alpha_rad))/(math.sin(beta_rad + delta_rad)*math.sin(beta_rad + alpha_rad))))**2
            return num / (den1 * den2) if den1*den2 != 0 else 0
    return 0.0

def resolver(caso: Caso) -> Resultado:
    filas, zs, esf_suelo, esf_agua, esf_carga, esf_sismo = [], [], [], [], [], []
    H = caso.altura
    dz = 0.001 
    puntos_z = [i * dz for i in range(int(H / dz) + 1)]
    if puntos_z[-1] < H: puntos_z.append(H)
    sigma_v, z_anterior = 0.0, 0.0

    for z in puntos_z:
        z_acumulado, estrato_actual, num_est = 0.0, caso.estratos[-1], len(caso.estratos)
        for i, est in enumerate(caso.estratos):
            z_acumulado += est.h
            if z <= z_acumulado + 1e-5: 
                estrato_actual = est; num_est = i + 1; break
                
        es_saturado = caso.z_agua is not None and z > caso.z_agua
        gamma_usar = estrato_actual.gamma_sat if es_saturado else estrato_actual.gamma
        delta_z = z - z_anterior
        
        if es_saturado and caso.z_agua is not None and z_anterior < caso.z_agua:
            sigma_v += ((caso.z_agua - z_anterior) * estrato_actual.gamma) + ((z - caso.z_agua) * (estrato_actual.gamma_sat - caso.gamma_agua))
        else:
            sigma_v += delta_z * ((estrato_actual.gamma_sat - caso.gamma_agua) if es_saturado else estrato_actual.gamma)

        K = calcular_K(estrato_actual.phi, caso.alpha, caso.beta, estrato_actual.delta, caso.condicion, caso.metodo)
        raiz_K = math.sqrt(K) if K > 0 else 0
        p_suelo = (K * sigma_v)
        if caso.condicion == 'activa': p_suelo = max(0, p_suelo - 2 * estrato_actual.cohesion * raiz_K)
        elif caso.condicion == 'pasiva': p_suelo += 2 * estrato_actual.cohesion * raiz_K

        p_agua = (z - caso.z_agua) * caso.gamma_agua if es_saturado else 0.0
        p_carga = sum(c.magnitud * K for c in caso.cargas if c.tipo.lower() in ['uniforme', 'franja'])
        p_sismo = (0.75 * caso.kh) * gamma_usar * z if (caso.kh > 0 and caso.condicion == 'activa') else 0.0

        p_total = p_suelo + p_agua + p_carga + p_sismo
        filas.append(FilaResultado(z, num_est, sigma_v, K, p_suelo, p_agua, p_carga, p_sismo, p_total))
        zs.append(z); esf_suelo.append(p_suelo); esf_agua.append(p_agua); esf_carga.append(p_carga); esf_sismo.append(p_sismo)
        z_anterior = z

    def integrar(presiones, profundidades):
        F, M_corona = 0.0, 0.0
        for i in range(len(profundidades)-1):
            z1, z2, p1, p2 = profundidades[i], profundidades[i+1], presiones[i], presiones[i+1]
            h = z2 - z1
            dF = (p1 + p2) * h / 2.0
            zc = z1 + h/2 if (p1 + p2) == 0 else z1 + h * (2*p2 + p1) / (3*(p1 + p2))
            F += dF; M_corona += dF * zc
        y_barra = (H - (M_corona / F)) if F > 1e-9 else 0.0
        return F, F * y_barra, y_barra

    P_s, M_s, y_s = integrar(esf_suelo, zs)
    P_w, M_w, y_w = integrar(esf_agua, zs)
    P_c, M_c, y_c = integrar(esf_carga, zs)
    P_e, M_e, y_e = integrar(esf_sismo, zs)
    P_tot, M_tot = P_s + P_w + P_c + P_e, M_s + M_w + M_c + M_e
    y_tot = (M_tot / P_tot) if P_tot > 1e-9 else 0.0
    comp = {'Suelo': (P_s, M_s, y_s), 'Agua': (P_w, M_w, y_w), 'Sobrecarga': (P_c, M_c, y_c), 'Incremento sísmico': (P_e, M_e, y_e)}

    # --- DESGLOSE GEOMÉTRICO EXTENDIDO ---
    detalles = []
    area_idx = 1
    
    def extraer_detalles(p_array, nombre_comp):
        nonlocal area_idx
        chunks, chunk_z, chunk_p = [], [], []
        z_agua_eval = caso.z_agua if caso.z_agua is not None else 9999
        current_id = f"{filas[0].estrato}_{filas[0].z > z_agua_eval}"
        
        for f, p_val in zip(filas, p_array):
            c_id = f"{f.estrato}_{f.z > z_agua_eval}"
            if c_id != current_id:
                chunks.append((chunk_z, chunk_p)); chunk_z, chunk_p = [f.z], [p_val]
                current_id = c_id
            else:
                chunk_z.append(f.z); chunk_p.append(p_val)
        if chunk_z: chunks.append((chunk_z, chunk_p))
            
        for z_arr, p_arr in chunks:
            if max(p_arr) < 1e-9: continue
            z_top, z_bot = z_arr[0], z_arr[-1]
            p_top, p_bot = p_arr[0], p_arr[-1]
            h_tramo = z_bot - z_top
            
            if h_tramo > 0.05:
                if abs(p_bot - p_top) > 0.01 and p_bot > 0.01 and p_top > 0.01:
                    min_p = min(p_top, p_bot)
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Rectángulo', min_p * h_tramo, z_top + h_tramo/2, H - (z_top + h_tramo/2), min_p / 2.0, min_p, h_tramo))
                    area_idx += 1
                    F_tri = abs(p_bot - p_top) * h_tramo / 2.0
                    zc_tri = z_top + h_tramo*(2/3) if p_bot > p_top else z_top + h_tramo*(1/3)
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', F_tri, zc_tri, H - zc_tri, min_p + abs(p_bot - p_top)/3.0, abs(p_bot - p_top), h_tramo))
                    area_idx += 1
                elif p_bot > 0.01 and p_top <= 0.01:
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', p_bot * h_tramo / 2.0, z_top + h_tramo*(2/3), H - (z_top + h_tramo*(2/3)), p_bot / 3.0, p_bot, h_tramo))
                    area_idx += 1
                elif p_top > 0.01 and p_bot <= 0.01:
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', p_top * h_tramo / 2.0, z_top + h_tramo*(1/3), H - (z_top + h_tramo*(1/3)), p_top / 3.0, p_top, h_tramo))
                    area_idx += 1
                else:
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Rectángulo', p_top * h_tramo, z_top + h_tramo/2, H - (z_top + h_tramo/2), p_top / 2.0, p_top, h_tramo))
                    area_idx += 1

    extraer_detalles([f.suelo for f in filas], 'Suelo')
    extraer_detalles([f.agua for f in filas], 'Agua')
    extraer_detalles([f.carga for f in filas], 'Sobrecarga')
    extraer_detalles([f.sismo for f in filas], 'Sismo')

    return Resultado(caso=caso, filas=filas, total=P_tot, momento=M_tot, y=y_tot, componentes=comp, detalles=detalles, notas=["Cálculo completado exitosamente."])