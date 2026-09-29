"""
Módulo de Gráficos Geotécnicos con Matplotlib.
Renderiza el perfil y los polígonos de presión.
Sistema visual limpio: Muestra las líneas de acción parciales sin saturar 
de texto la gráfica (el texto se reserva solo para la Resultante Total).
"""
import math
from matplotlib.figure import Figure
import matplotlib.patches as patches

def renderizar_perfil(ax, altura, estratos, cargas=None, nf_val=None, alpha=0.0, beta=90.0, tipo_muro="Rectangular", modo_muro="Genérico", b_base=2.0, e_pantalla=0.5, unidad_L="m"):
    ax.clear(); ax.axis('off') 
    H = altura
    if H <= 0: return
    
    beta_plot = 89.0 if (tipo_muro == "Trapezoidal" and beta >= 90.0) else beta

    def x_desplazamiento(z_val):
        if abs(beta_plot - 90.0) < 1e-5: return 0.0
        return - (H - z_val) / math.tan(math.radians(beta_plot))

    desp_corona = x_desplazamiento(0.0)
    
    if tipo_muro == "Trapezoidal":
        b, e = b_base, e_pantalla
        if modo_muro == "Personalizado":
            if b <= e: b = e + 0.1
            beta_plot = math.degrees(math.atan2(H, (b - e) / 2.0))
        else:
            e = 0.5; b = max(e + 0.1, e - 2 * desp_corona) 
        center = b / 2.0
        x_bot_izq, x_bot_der = center - b / 2.0, center + b / 2.0
        x_top_izq, x_top_der = center - e / 2.0, center + e / 2.0
    else:
        b = b_base if modo_muro == "Personalizado" else 0.5
        x_bot_izq, x_bot_der = 0.0, b
        x_top_izq, x_top_der = x_bot_izq + desp_corona, x_bot_der + desp_corona
        
    pts_muro = [[x_top_izq, 0], [x_top_der, 0], [x_bot_der, H], [x_bot_izq, H]]
    ax.add_patch(patches.Polygon(pts_muro, facecolor='#5c5c5c', edgecolor='black', linewidth=1.5))
    
    def x_trasdos(z_val): return x_top_der + (x_bot_der - x_top_der) * (z_val / H)
    X_MAX = max(x_bot_der, x_top_der) + (2.0 * H)
    def z_surf(x_val): return - (x_val - x_top_der) * math.tan(math.radians(alpha))
    
    ax.set_xlim(min(x_bot_izq, x_top_izq) - 2.2, X_MAX + 4.5)
    limite_superior = min(-1.5, z_surf(X_MAX) - 1.5)
    if cargas and len(cargas) > 0: limite_superior -= 1.0 
    ax.set_ylim(H + 1.0, limite_superior)
    ax.set_aspect('equal')
    
    z_acc = 0.0
    colores = ['#e6ccb2', '#ddb892', '#b08968', '#7f5539', '#5c3a21']
    geometrias_estratos = []

    if not estratos:
        pts = [[x_top_der, 0], [X_MAX, z_surf(X_MAX)], [X_MAX, H], [x_bot_der, H]]
        ax.add_patch(patches.Polygon(pts, facecolor='#f0e6d2', alpha=0.5, edgecolor='black', linestyle='--'))
        ax.text((x_top_der + X_MAX)/2, H/2, "Sin estratos", ha='center', va='center', color='gray', fontweight='bold')
    else:
        for i, est in enumerate(estratos):
            z_bot = min(z_acc + est.h, H)
            x_top_left, x_bot_left = x_trasdos(z_acc), x_trasdos(z_bot)
            z_top_label = z_surf(X_MAX) if i == 0 else z_acc
            
            pts = [[x_top_left, z_acc], [X_MAX, z_top_label], [X_MAX, z_bot], [x_bot_left, z_bot]]
            ax.add_patch(patches.Polygon(pts, facecolor=colores[i % len(colores)], alpha=0.7, edgecolor='black'))
            
            xc = (max(x_top_left, x_bot_left) + X_MAX) / 2.0
            
            if nf_val is not None:
                if z_bot <= nf_val + 1e-5:
                    ax.text(xc, (z_top_label + z_bot)/2.0, f"Estrato {i+1}\nγ = {est.gamma}\nφ' = {est.phi}°\nc' = {est.cohesion}", ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.85, edgecolor='#ccc'))
                elif z_top_label >= nf_val - 1e-5:
                    ax.text(xc, (z_top_label + z_bot)/2.0, f"Estrato {i+1}\nγsat = {est.gamma_sat}\nφ' = {est.phi}°\nc' = {est.cohesion}", ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.85, edgecolor='#ccc'))
                else:
                    ax.text(xc, (z_top_label + nf_val)/2.0, f"Estrato {i+1}\nγ = {est.gamma}\nφ' = {est.phi}°\nc' = {est.cohesion}", ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.85, edgecolor='#ccc'))
                    ax.text(xc, (nf_val + z_bot)/2.0, f"Estrato {i+1}\nγsat = {est.gamma_sat}\nφ' = {est.phi}°\nc' = {est.cohesion}", ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.85, edgecolor='#ccc'))
            else:
                ax.text(xc, (z_top_label + z_bot)/2.0, f"Estrato {i+1}\nγ = {est.gamma}\nφ' = {est.phi}°\nc' = {est.cohesion}", ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.85, edgecolor='#ccc'))
                
            geometrias_estratos.append((z_acc, z_bot, est.h))
            z_acc = z_bot
            if z_acc >= H: break

    if cargas:
        for c in cargas:
            try: tipo, mag, a_dist, b_dist = str(c[0]).strip().lower(), float(c[1]), float(c[2]), float(c[3])
            except (ValueError, IndexError): continue
            
            x_start = x_top_der if tipo == 'uniforme' else x_top_der + a_dist
            x_end = X_MAX if tipo == 'uniforme' else (x_start + b_dist if tipo == 'franja' else x_start + 0.1)
            z1, z2 = z_surf(x_start), z_surf(x_end)

            if tipo in ['uniforme', 'franja']:
                h_c = 0.6  
                ax.add_patch(patches.Polygon([[x_start, z1], [x_start, z1 - h_c], [x_end, z2 - h_c], [x_end, z2]], facecolor='#cc3333', alpha=0.6, edgecolor='darkred'))
                ax.text((x_start + x_end) / 2, (z1 + z2) / 2 - h_c / 2, f"q={mag}", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
            else:
                ax.annotate('', xy=(x_start, z1), xytext=(x_start, z1 - 1.2), arrowprops=dict(arrowstyle='->', color='darkred', lw=2.5))
                ax.text(x_start, z1 - 1.4, f"Q={mag}", ha='center', va='bottom', color='darkred', fontsize=8, fontweight='bold')

    if nf_val is not None and nf_val < H:
        zw = nf_val
        ax.plot([x_trasdos(zw), X_MAX], [zw, zw], color='#0066cc', linestyle='--', linewidth=1.5)
        dx, dy = max(0.1, H * 0.01), max(0.2, H * 0.02)
        xt = X_MAX - dx * 10
        ax.plot([xt, xt-dx, xt+dx, xt], [zw, zw-dy, zw-dy, zw], color='#0066cc', lw=1.2)
        ax.text(xt + dx*2.0, zw - dy*0.3, f"NF (z = {zw}{unidad_L})", color='#0066cc', fontsize=8, va='bottom', fontweight='bold', ha='left')

    ax.plot([x_bot_der, x_bot_der + 1.2], [H, H], color='black', linestyle='--', lw=0.9)
    ax.text(x_bot_der + 0.2, H - 0.2, f"β = {beta_plot:.1f}°", color='blue', fontsize=8, fontweight='bold')
    ax.plot([x_top_der, x_top_der + 1.2], [0, 0], color='black', linestyle='--', lw=0.9)
    ax.text(x_top_der + 0.4, -0.2, f"α = {alpha}°", color='purple', fontsize=8, fontweight='bold')

    x_cota_h_izq = min(x_bot_izq, x_top_izq) - 0.8
    ax.plot([x_cota_h_izq - 0.05, x_cota_h_izq + 0.05], [0, 0], color='black', lw=0.8)
    ax.plot([x_cota_h_izq - 0.05, x_cota_h_izq + 0.05], [H, H], color='black', lw=0.8)
    ax.annotate('', xy=(x_cota_h_izq, 0), xytext=(x_cota_h_izq, H), arrowprops=dict(arrowstyle='<->', color='black', lw=1))
    ax.text(x_cota_h_izq - 0.15, H / 2, f"H = {H:.1f} {unidad_L}", rotation=90, va='center', ha='right', fontsize=9, fontweight='bold')

    x_cota_parcial, x_cota_total = X_MAX + 0.8, X_MAX + 2.5      
    for z_a, z_b, h_e in geometrias_estratos:
        if nf_val is not None and z_a < nf_val < z_b:
            ax.plot([x_cota_parcial - 0.1, x_cota_parcial + 0.1], [z_a, z_a], color='black', lw=0.8)
            ax.plot([x_cota_parcial - 0.1, x_cota_parcial + 0.1], [nf_val, nf_val], color='black', lw=0.8)
            ax.annotate('', xy=(x_cota_parcial, z_a), xytext=(x_cota_parcial, nf_val), arrowprops=dict(arrowstyle='<->', color='#333333', lw=0.8))
            ax.text(x_cota_parcial, (z_a + nf_val) / 2, f"{nf_val - z_a:.1f} {unidad_L}", va='center', ha='center', fontsize=8, bbox=dict(facecolor='white', edgecolor='none', pad=1))
            
            ax.plot([x_cota_parcial - 0.1, x_cota_parcial + 0.1], [z_b, z_b], color='black', lw=0.8)
            ax.annotate('', xy=(x_cota_parcial, nf_val), xytext=(x_cota_parcial, z_b), arrowprops=dict(arrowstyle='<->', color='#333333', lw=0.8))
            ax.text(x_cota_parcial, (nf_val + z_b) / 2, f"{z_b - nf_val:.1f} {unidad_L}", va='center', ha='center', fontsize=8, bbox=dict(facecolor='white', edgecolor='none', pad=1))
        
        ax.plot([x_cota_total - 0.1, x_cota_total + 0.1], [z_a, z_a], color='black', lw=0.8)
        ax.plot([x_cota_total - 0.1, x_cota_total + 0.1], [z_b, z_b], color='black', lw=0.8)
        ax.annotate('', xy=(x_cota_total, z_a), xytext=(x_cota_total, z_b), arrowprops=dict(arrowstyle='<->', color='black', lw=1))
        ax.text(x_cota_total, (z_a + z_b) / 2, f"{h_e:.1f} {unidad_L}", va='center', ha='center', fontsize=8, fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', pad=1))

    ax.set_title("Perfil Geotécnico y Estratigrafía", fontweight='bold', fontsize=10)

def renderizar_presiones(ax, resultado, scale_z=1.0, scale_p=1.0, unidad_p="kPa", unidad_z="m", scale_F=1.0, unidad_F="kN/m", visibles=None):
    if visibles is None:
        visibles = {'Suelo': True, 'Agua': True, 'Sobrecarga': True, 'Sismo': True, 'Vectores': True}
        
    ax.clear(); ax.axis('on')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.grid(False)
    if not resultado: return
    
    H_disp = resultado.caso.altura * scale_z
    beta = resultado.caso.beta
    tan_t = math.tan(math.radians(resultado.caso.alpha))
    
    def x_muro(z_disp):
        if abs(beta - 90.0) < 1e-5: return 0.0
        return z_disp / math.tan(math.radians(beta))
        
    ax.plot([x_muro(0), x_muro(H_disp)], [0, H_disp], color='black', linewidth=1.5)
    
    def sumar_presiones_visibles(f):
        s = 0.0
        if visibles['Suelo']: s += f.suelo
        if visibles['Agua']: s += f.agua
        if visibles['Sobrecarga']: s += f.carga
        if visibles['Sismo']: s += f.sismo
        return s
        
    max_p_vis = max(max(sumar_presiones_visibles(f) * scale_p for f in resultado.filas), 1.0 * scale_p)
    max_x_bound = max_p_vis * 1.25
    ratio_z_x = H_disp / max_x_bound
    t_box = dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1.0)
    
    def transform(z_disp, p_scaled):
        return x_muro(z_disp) + p_scaled, z_disp - (p_scaled * ratio_z_x) * tan_t

    def dibujar_formas_relleno(p_si_array, color_fill, color_line, is_water=False):
        p_scaled_array = [p * scale_p for p in p_si_array]
        if max(p_scaled_array) < 1e-9: return
        
        chunks, chunk_z, chunk_p = [], [], []
        z_agua_eval = resultado.caso.z_agua if resultado.caso.z_agua is not None else 9999
        current_id = f"{resultado.filas[0].estrato}_{resultado.filas[0].z > z_agua_eval}"
        
        for f, p_val in zip(resultado.filas, p_scaled_array):
            c_id = f"{f.estrato}_{f.z > z_agua_eval}"
            z_disp = f.z * scale_z
            if c_id != current_id:
                chunks.append((chunk_z, chunk_p)); chunk_z, chunk_p = [z_disp], [p_val]
                current_id = c_id
            else:
                chunk_z.append(z_disp); chunk_p.append(p_val)
        if chunk_z: chunks.append((chunk_z, chunk_p))
        
        for z_arr, p_arr in chunks:
            if max(p_arr) < 1e-9: continue
            pts = [(x_muro(z), z) for z in z_arr] 
            pts += [transform(z, p) for z, p in zip(reversed(z_arr), reversed(p_arr))] 
            ax.add_patch(patches.Polygon(pts, facecolor=color_fill, alpha=0.9, edgecolor='none'))
            
            out_x, out_z = [], []
            for z, p in zip(z_arr, p_arr):
                x_v, z_v = transform(z, p); out_x.append(x_v); out_z.append(z_v)
            ax.plot(out_x, out_z, color=color_line, linestyle='--' if is_water else '-', linewidth=1.5)
            
            z_top, z_bot = z_arr[0], z_arr[-1]
            p_top, p_bot = p_arr[0], p_arr[-1]
            
            if z_bot < H_disp - 0.001:
                x1, z1 = x_muro(z_bot), z_bot; x2, z2 = transform(z_bot, p_bot)
                ax.plot([x1, x2], [z1, z2], color='gray', linestyle=':', linewidth=1.2)
                
            xt, zt = transform(z_top, p_top)
            xb, zb = transform(z_bot, p_bot)
            if p_top > 0.01: ax.text(xt, zt, f" {p_top:.2f}", va='bottom', ha='left', fontsize=8, bbox=t_box)
            if p_bot > 0.01 and abs(p_bot - p_top) > 0.01: ax.text(xb, zb, f" {p_bot:.2f}", va='top', ha='left', fontsize=8, bbox=t_box)
                
            h_tramo = z_bot - z_top
            if h_tramo > 0.05 * scale_z:
                if abs(p_bot - p_top) > 0.01 and p_bot > 0.01 and p_top > 0.01:
                    min_p = min(p_top, p_bot)
                    x1, z1 = transform(z_top, min_p); x2, z2 = transform(z_bot, min_p)
                    ax.plot([x1, x2], [z1, z2], color=color_line, linestyle='--', linewidth=0.8, alpha=0.7)

    if visibles['Suelo']: dibujar_formas_relleno([f.suelo for f in resultado.filas], '#eaf5ea', '#2ca02c')
    if visibles['Agua']: dibujar_formas_relleno([f.agua for f in resultado.filas], '#cce5ff', '#0066cc', is_water=True)
    if visibles['Sobrecarga']: dibujar_formas_relleno([f.carga for f in resultado.filas], '#ffe6cc', '#ff7f0e')
    if visibles['Sismo']: dibujar_formas_relleno([f.sismo for f in resultado.filas], '#ffeded', '#d62728')

    x_start_tot = max_x_bound * 1.15
    colores_comp = {'Suelo': '#2ca02c', 'Agua': '#0066cc', 'Sobrecarga': '#ff7f0e', 'Sismo': '#d62728'}
    used_z = []

    sum_P, sum_M = 0.0, 0.0
    if visibles['Suelo']: sum_P += resultado.componentes['Suelo'][0]; sum_M += resultado.componentes['Suelo'][1]
    if visibles['Agua']: sum_P += resultado.componentes['Agua'][0]; sum_M += resultado.componentes['Agua'][1]
    if visibles['Sobrecarga']: sum_P += resultado.componentes['Sobrecarga'][0]; sum_M += resultado.componentes['Sobrecarga'][1]
    if visibles['Sismo']: sum_P += resultado.componentes['Incremento sísmico'][0]; sum_M += resultado.componentes['Incremento sísmico'][1]

    if visibles.get('Vectores', True):
        for d in resultado.detalles:
            if not visibles.get(d.componente, True): continue
            if d.fuerza * scale_F < 0.05: continue
            
            circle_num = chr(0x245f + d.id) if 1 <= d.id <= 20 else f"({d.id})"
            z_c = d.z_centro * scale_z
            pc_scaled = d.p_centro * scale_p
            color_arrow = colores_comp.get(d.componente, 'gray')
            
            xc, zc_shape = transform(z_c, pc_scaled)
            ax.text(xc, zc_shape, circle_num, ha='center', va='center', fontsize=11, color=color_arrow, bbox=t_box)
            
            z_arrow = z_c
            for uz in used_z:
                if abs(uz - z_arrow) < H_disp * 0.06: z_arrow += H_disp * 0.06
            used_z.append(z_arrow)
            x_wall = x_muro(z_arrow)
            
            # Línea pura de acción parcial, sin el texto superpuesto
            ax.annotate('', xy=(x_wall, z_arrow), xytext=(x_start_tot * 0.7, z_arrow), arrowprops=dict(arrowstyle='->', color=color_arrow, lw=1.2, alpha=0.9))
                    
        if sum_P * scale_F > 0.05:
            Y_T = (sum_M / sum_P) * scale_z
            z_T = H_disp - Y_T
            x_wall = x_muro(z_T)
            
            ax.annotate('', xy=(x_wall, z_T), xytext=(x_start_tot * 1.35, z_T), arrowprops=dict(facecolor='#cc0000', edgecolor='#cc0000', width=2.5, headwidth=8))
            
            lbl_title = "E_TOTAL" if all([v for k, v in visibles.items() if k != 'Vectores']) else "E_PARCIAL"
            ax.text(x_start_tot * 1.38, z_T, f"{lbl_title} = {sum_P*scale_F:.2f} {unidad_F}\ny_T = {Y_T:.2f} {unidad_z}", 
                    va='top', ha='left', color='#cc0000', fontweight='bold', fontsize=9, bbox=t_box)
            ax.set_xlim(min(0, -max_x_bound * 0.1), max_x_bound * 2.2)
        else:
            ax.set_xlim(min(0, -max_x_bound * 0.1), max_x_bound * 1.2)
    else:
        ax.set_xlim(min(0, -max_x_bound * 0.1), max_x_bound * 1.2)

    min_z = min(-0.5, - H_disp * abs(tan_t) * 1.5)
    ax.set_ylim(H_disp + 0.5, min_z) 
    
    import matplotlib.lines as mlines
    leyenda = []
    if visibles['Suelo']: leyenda.append(mlines.Line2D([0], [0], color=colores_comp['Suelo'], lw=1.5, label='Suelo'))
    if visibles['Agua']: leyenda.append(mlines.Line2D([0], [0], color=colores_comp['Agua'], lw=1.5, linestyle='--', label='Agua'))
    if visibles['Sobrecarga']: leyenda.append(mlines.Line2D([0], [0], color=colores_comp['Sobrecarga'], lw=1.5, label='Sobrecargas'))
    if visibles['Sismo']: leyenda.append(mlines.Line2D([0], [0], color=colores_comp['Sismo'], lw=1.5, label='Sismo'))
    
    if leyenda: ax.legend(handles=leyenda, loc="best", fontsize=8, framealpha=0.9)
    ax.set_xlabel(f"Presión horizontal ({unidad_p})", fontsize=9)
    ax.set_ylabel(f"Profundidad z ({unidad_z})", fontsize=9)
    ax.set_xticks([])
    ax.set_title("Esfuerzos Horizontales Analíticos", fontweight='bold', fontsize=10)