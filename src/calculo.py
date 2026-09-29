"""
Módulo de Cálculo Geotécnico.
Aplica estrictamente las fórmulas del curso:
- Coulomb / Rankine para K estático.
- Mononobe-Okabe para K dinámico (Sismo).
- Jarquio (1981) para fuerzas de sobrecargas finitas.
- Boussinesq Modificado para el dibujo del bulbo de presiones.
- Integración matemática de esfuerzos negativos (Grietas de tracción).
"""
import math
from modelos import Caso, Resultado, FilaResultado, AreaDetalle

def calcular_K_estatico(phi, alpha, beta, delta, condicion, metodo):
    phi_r, alpha_r, beta_r, delta_r = map(math.radians, [phi, alpha, beta, delta])
    
    if condicion == 'reposo':
        return 1.0 - math.sin(phi_r)
        
    if metodo == 'Rankine':
        cos_a = math.cos(alpha_r)
        raiz = math.sqrt(abs(math.cos(alpha_r)**2 - math.cos(phi_r)**2))
        if condicion == 'activa':
            return cos_a * ((cos_a - raiz) / (cos_a + raiz))
        else:
            return cos_a * ((cos_a + raiz) / (cos_a - raiz))
            
    if metodo == 'Coulomb':
        sen_b = math.sin(beta_r)
        if condicion == 'activa':
            num = math.sin(beta_r + phi_r)**2
            den1 = sen_b**2 * math.sin(beta_r - delta_r)
            val_raiz = (math.sin(phi_r + delta_r)*math.sin(phi_r - alpha_r))/(math.sin(beta_r - delta_r)*math.sin(alpha_r + beta_r))
            if val_raiz < 0: val_raiz = 0
            den2 = (1.0 + math.sqrt(val_raiz))**2
            return num / (den1 * den2) if den1*den2 != 0 else 0.0
        else: 
            num = math.sin(beta_r - phi_r)**2
            den1 = sen_b**2 * math.sin(beta_r + delta_r)
            val_raiz = (math.sin(phi_r + delta_r)*math.sin(phi_r + alpha_r))/(math.sin(beta_r + delta_r)*math.sin(alpha_r + beta_r))
            if val_raiz < 0: val_raiz = 0
            den2 = (1.0 - math.sqrt(val_raiz))**2
            return num / (den1 * den2) if den1*den2 != 0 else 0.0
    return 0.0

def calcular_K_dinamico(phi, alpha, beta, delta, kh, kv):
    if kh == 0 and kv == 0: return 0.0
    theta_r = math.atan(kh / (1.0 - kv))
    phi_r, alpha_r, beta_r, delta_r = map(math.radians, [phi, alpha, beta, delta])
    
    num = math.sin(beta_r + phi_r - theta_r)**2
    den1 = math.cos(theta_r) * math.sin(beta_r)**2 * math.sin(beta_r - delta_r - theta_r)
    val_raiz = (math.sin(phi_r + delta_r)*math.sin(phi_r - alpha_r - theta_r))/(math.sin(beta_r - delta_r - theta_r)*math.sin(alpha_r + beta_r))
    if val_raiz < 0: val_raiz = 0 
    den2 = (1.0 + math.sqrt(val_raiz))**2
    return num / (den1 * den2) if den1*den2 != 0 else 0.0

def boussinesq_franja(q, a_p, b_p, z):
    if z <= 0: return 0.0
    beta_rad = math.atan((a_p + b_p)/z) - math.atan(a_p/z)
    alpha_rad = math.atan(z/(a_p + b_p))
    return (2.0 * q / math.pi) * (beta_rad - math.sin(beta_rad)*math.cos(2.0*alpha_rad))

def resolver(caso: Caso) -> Resultado:
    filas = []
    H = caso.altura
    dz = 0.005 
    puntos_z = [i * dz for i in range(int(H / dz) + 1)]
    if puntos_z[-1] < H: puntos_z.append(H)
    
    sigma_v = 0.0
    z_anterior = 0.0

    for z in puntos_z:
        z_acumulado, est_actual, num_est = 0.0, caso.estratos[-1], len(caso.estratos)
        for i, est in enumerate(caso.estratos):
            z_acumulado += est.h
            if z <= z_acumulado + 1e-5: 
                est_actual = est; num_est = i + 1; break
                
        es_sat = caso.z_agua is not None and z > caso.z_agua
        gamma_usar = est_actual.gamma_sat if es_sat else est_actual.gamma
        delta_z = z - z_anterior
        
        if es_sat and caso.z_agua is not None and z_anterior < caso.z_agua:
            sigma_v += ((caso.z_agua - z_anterior) * est_actual.gamma) + ((z - caso.z_agua) * (est_actual.gamma_sat - caso.gamma_agua))
        else:
            sigma_v += delta_z * ((est_actual.gamma_sat - caso.gamma_agua) if es_sat else est_actual.gamma)

        Ka = calcular_K_estatico(est_actual.phi, caso.alpha, caso.beta, est_actual.delta, caso.condicion, caso.metodo)
        raiz_K = math.sqrt(Ka) if Ka > 0 else 0
        
        # --- LIBERACIÓN DEL LÍMITE NEGATIVO ---
        p_suelo = (Ka * sigma_v)
        if caso.condicion == 'activa': p_suelo = p_suelo - 2 * est_actual.cohesion * raiz_K
        elif caso.condicion == 'pasiva': p_suelo += 2 * est_actual.cohesion * raiz_K

        p_agua = (z - caso.z_agua) * caso.gamma_agua if es_sat else 0.0
        
        p_carga_inf = sum(c.magnitud * Ka for c in caso.cargas if c.tipo.lower() == 'uniforme')
        p_carga_finita = sum(boussinesq_franja(c.magnitud, c.a, c.b, z) for c in caso.cargas if c.tipo.lower() == 'franja')
        p_carga_total = p_carga_inf + p_carga_finita
        
        p_total = p_suelo + p_agua + p_carga_total
        filas.append(FilaResultado(z, num_est, sigma_v, Ka, p_suelo, p_agua, p_carga_total, 0.0, p_total, p_carga_inf))
        z_anterior = z

    def integrar_columna(attr):
        F, M = 0.0, 0.0
        for i in range(len(filas)-1):
            z1, z2 = filas[i].z, filas[i+1].z
            p1, p2 = getattr(filas[i], attr), getattr(filas[i+1], attr)
            h_tr = z2 - z1
            dF = (p1 + p2) * h_tr / 2.0
            zc = z1 + h_tr/2 if (p1 + p2) == 0 else z1 + h_tr * (2*p2 + p1) / (3*(p1 + p2))
            F += dF
            M += dF * zc
        y_b = (H - (M / F)) if abs(F) > 1e-9 else 0.0
        return F, F * y_b, y_b

    P_s, M_s, y_s = integrar_columna('suelo')
    P_w, M_w, y_w = integrar_columna('agua')
    P_c_inf, M_c_inf, y_c_inf = integrar_columna('carga_inf')
    
    P_c_finita, M_c_finita = 0.0, 0.0
    for c in caso.cargas:
        if c.tipo.lower() == 'franja':
            b_prime = c.a 
            a_prime = c.b  
            theta1 = math.degrees(math.atan(b_prime / H))
            theta2 = math.degrees(math.atan((a_prime + b_prime) / H))
            
            if (theta2 - theta1) > 0:
                P_q = (c.magnitud / 90.0) * (H * (theta2 - theta1))
                R = ((a_prime + b_prime)**2) * (90.0 - theta2)
                Q = (b_prime**2) * (90.0 - theta1)
                num_y = (H**2)*(theta2 - theta1) + (R - Q) - 57.3 * a_prime * H
                y_q = H - (num_y / (2.0 * H * (theta2 - theta1)))
                
                P_c_finita += P_q
                M_c_finita += (P_q * y_q)
                
    P_c_total = P_c_inf + P_c_finita
    M_c_total = M_c_inf + M_c_finita
    y_c_total = M_c_total / P_c_total if abs(P_c_total) > 1e-9 else 0.0
    
    y_c_finita = M_c_finita / P_c_finita if abs(P_c_finita) > 1e-9 else 0.0

    P_sismo_neto, M_sismo_neto, y_sismo_neto = 0.0, 0.0, 0.0
    if caso.kh > 0 and caso.condicion == 'activa':
        F_din, M_din_corona = 0.0, 0.0
        for i in range(len(filas)-1):
            z1, z2 = filas[i].z, filas[i+1].z
            sv1, sv2 = filas[i].sigma_v, filas[i+1].sigma_v
            est_id = filas[i].estrato
            est = caso.estratos[est_id - 1]
            
            Kae = calcular_K_dinamico(est.phi, caso.alpha, caso.beta, est.delta, caso.kh, caso.kv)
            p1_din, p2_din = sv1 * Kae, sv2 * Kae
            
            h_tr = z2 - z1
            dF = (p1_din + p2_din) * h_tr / 2.0
            zc = z1 + h_tr/2 if (p1_din + p2_din) == 0 else z1 + h_tr * (2*p2_din + p1_din) / (3*(p1_din + p2_din))
            F_din += dF
            M_din_corona += dF * zc
            
            filas[i].sismo = p1_din - max(0, filas[i].suelo)
            filas[i].total = filas[i].suelo + filas[i].agua + filas[i].carga + filas[i].sismo
            
        last_est_id = filas[-1].estrato
        last_est = caso.estratos[last_est_id - 1]
        Kae_last = calcular_K_dinamico(last_est.phi, caso.alpha, caso.beta, last_est.delta, caso.kh, caso.kv)
        p_last_din = filas[-1].sigma_v * Kae_last
        filas[-1].sismo = p_last_din - max(0, filas[-1].suelo)
        filas[-1].total = filas[-1].suelo + filas[-1].agua + filas[-1].carga + filas[-1].sismo
            
        P_ae = F_din
        Delta_Pae = P_ae - P_s 
        P_sismo_neto = Delta_Pae
        y_sismo_neto = 0.6 * H 
        M_sismo_neto = P_sismo_neto * y_sismo_neto

    P_tot = P_s + P_w + P_c_total + P_sismo_neto
    M_tot = M_s + M_w + M_c_total + M_sismo_neto
    y_tot = (M_tot / P_tot) if abs(P_tot) > 1e-9 else 0.0
    
    comp = {
        'Suelo': (P_s, M_s, y_s), 
        'Agua': (P_w, M_w, y_w), 
        'Sobrecarga': (P_c_total, M_c_total, y_c_total), 
        'Incremento sísmico': (P_sismo_neto, M_sismo_neto, y_sismo_neto)
    }

    detalles = []
    area_idx = 1
    
    def extraer_detalles(attr, nombre_comp):
        nonlocal area_idx
        chunks, chunk_z, chunk_p = [], [], []
        z_agua_eval = caso.z_agua if caso.z_agua is not None else 9999.0
        current_id = f"{filas[0].estrato}_{filas[0].z > z_agua_eval}"
        
        for f in filas:
            p_val = getattr(f, attr)
            c_id = f"{f.estrato}_{f.z > z_agua_eval}"
            if c_id != current_id:
                chunks.append((chunk_z, chunk_p)); chunk_z, chunk_p = [f.z], [p_val]
                current_id = c_id
            else:
                chunk_z.append(f.z); chunk_p.append(p_val)
        if chunk_z: chunks.append((chunk_z, chunk_p))
            
        TOL = 0.1 
        
        # --- INTERPOLADOR Zc PARA PRESIONES NEGATIVAS ---
        # Corta matemáticamente las figuras que cruzan el cero
        new_chunks = []
        for z_arr, p_arr in chunks:
            p_top, p_bot = p_arr[0], p_arr[-1]
            if p_top * p_bot < -TOL: 
                h_tr = z_arr[-1] - z_arr[0]
                z_zero = z_arr[0] + h_tr * abs(p_top) / (abs(p_top) + abs(p_bot))
                new_chunks.append(([z_arr[0], z_zero], [p_top, 0.0]))
                new_chunks.append(([z_zero, z_arr[-1]], [0.0, p_bot]))
            else:
                new_chunks.append((z_arr, p_arr))

        for z_arr, p_arr in new_chunks:
            if all(abs(p) <= TOL for p in p_arr): continue
            z_top, z_bot = z_arr[0], z_arr[-1]
            p_top, p_bot = p_arr[0], p_arr[-1]
            h_tr = z_bot - z_top
            
            if h_tr > 0.05:
                if abs(p_bot) > TOL and abs(p_top) <= TOL:
                    F = (p_bot * h_tr) / 2.0
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', F, z_top + h_tr*(2/3), H - (z_top + h_tr*(2/3)), p_bot / 3.0, p_bot, h_tr))
                    area_idx += 1
                elif abs(p_top) > TOL and abs(p_bot) <= TOL:
                    F = (p_top * h_tr) / 2.0
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', F, z_top + h_tr*(1/3), H - (z_top + h_tr*(1/3)), p_top / 3.0, p_top, h_tr))
                    area_idx += 1
                else:
                    sign = 1 if p_top > 0 else -1
                    min_p_abs = min(abs(p_top), abs(p_bot))
                    min_p = min_p_abs * sign
                    
                    F_rect = min_p * h_tr
                    detalles.append(AreaDetalle(area_idx, nombre_comp, 'Rectángulo', F_rect, z_top + h_tr/2, H - (z_top + h_tr/2), min_p / 2.0, min_p, h_tr))
                    area_idx += 1
                    
                    if abs(p_bot - p_top) > TOL:
                        F_tri = (p_bot - p_top) * h_tr / 2.0
                        zc_tri = z_top + h_tr*(2/3) if abs(p_bot) > abs(p_top) else z_top + h_tr*(1/3)
                        detalles.append(AreaDetalle(area_idx, nombre_comp, 'Triángulo', F_tri, zc_tri, H - zc_tri, min_p + (p_bot - p_top)/3.0, (p_bot - p_top), h_tr))
                        area_idx += 1

    extraer_detalles('suelo', 'Suelo')
    extraer_detalles('agua', 'Agua')
    if P_c_inf > 0: extraer_detalles('carga_inf', 'Sobrecarga')
    if P_c_finita > 0:
        p_max_boussinesq = sum(boussinesq_franja(c.magnitud, c.a, c.b, H - y_c_finita) for c in caso.cargas if c.tipo.lower() == 'franja')
        detalles.append(AreaDetalle(area_idx, 'Sobrecarga', 'Bulbo Boussinesq (Jarquio)', P_c_finita, H - y_c_finita, y_c_finita, p_max_boussinesq / 2.0, P_c_finita, H))
        area_idx += 1 
        
    if abs(P_sismo_neto) > 0.05: 
        extraer_detalles('sismo', 'Sismo')

    return Resultado(caso=caso, filas=filas, total=P_tot, momento=M_tot, y=y_tot, componentes=comp, detalles=detalles, notas=["Cálculo incluye interpolación analítica de grietas de tracción (esfuerzos negativos)."])