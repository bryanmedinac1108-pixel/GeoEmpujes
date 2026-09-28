"""
Módulo de Gráficos Geotécnicos con Matplotlib.
Procesa el renderizado dinámico de la interfaz para el perfil y el cálculo numérico.

Avanzado: 
- Proyecta geométricamente los polígonos de presión utilizando la inclinación 
  del relleno (alpha) y del muro (beta) logrando representaciones idénticas a los libros de texto.
"""
import math
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.lines import Line2D

def renderizar_perfil(ax, altura, estratos, cargas=None, nf_val=None, alpha=0.0, beta=90.0, tipo_muro="Rectangular", modo_muro="Genérico", b_base=2.0, e_pantalla=0.5):
    """
    Dibuja el Perfil Físico Geotécnico (izquierdo).
    Muestra el muro, los estratos rellenados, el nivel freático, las cargas aplicadas 
    y evalúa qué peso unitario (γ o γsat) mostrar dependiendo del agua.
    """
    ax.clear()
    ax.axis('off') # Asegura ocultar ejes desde el principio
    
    H = altura
    if H <= 0: return
    
    # 1. Definición geométrica del polígono del Muro (Gris)
    beta_plot = beta
    if tipo_muro == "Trapezoidal" and beta >= 90.0:
        beta_plot = 89.0

    def x_desplazamiento(z_val):
        """Calcula el desfase horizontal (x) de la cara del muro a la profundidad z provocado por beta."""
        if abs(beta_plot - 90.0) < 1e-5: return 0.0
        return - (H - z_val) / math.tan(math.radians(beta_plot))

    desp_corona = x_desplazamiento(0.0)
    
    # Coordenadas X específicas del muro dependiendo si es cuadrado o trapecio
    if tipo_muro == "Trapezoidal":
        if modo_muro == "Personalizado":
            b = b_base
            e = e_pantalla
            if b <= e: 
                b = e + 0.1
            dx = (b - e) / 2.0
            beta_plot = math.degrees(math.atan2(H, dx))
        else:
            e = 0.5
            b = max(e + 0.1, e - 2 * desp_corona) 
            
        center = b / 2.0
        x_bot_izq = center - b / 2.0
        x_bot_der = center + b / 2.0
        x_top_izq = center - e / 2.0
        x_top_der = center + e / 2.0
    else:
        if modo_muro == "Personalizado":
            b = b_base
        else:
            b = 0.5
            
        x_bot_izq = 0.0
        x_bot_der = b
        x_top_izq = x_bot_izq + desp_corona
        x_top_der = x_bot_der + desp_corona
        
    pts_muro = [[x_top_izq, 0], [x_top_der, 0], [x_bot_der, H], [x_bot_izq, H]]
    muro = patches.Polygon(pts_muro, facecolor='#5c5c5c', edgecolor='black', linewidth=1.5)
    ax.add_patch(muro)
    
    # 2. Configuración del espacio de dibujo (Vista 'Camera')
    def x_trasdos(z_val):
        """Coordenada X exacta de la cara posterior del muro (contacto con el suelo) a la profundidad z."""
        return x_top_der + (x_bot_der - x_top_der) * (z_val / H)
    
    x_inicio_suelo = x_top_der
    ANCHO_ESTRATO = 2.0 * H
    X_MAX = max(x_bot_der, x_top_der) + ANCHO_ESTRATO
    
    def z_surf(x_val):
        """Coordenada Z de la superficie del suelo afectada por la inclinación alpha."""
        return - (x_val - x_inicio_suelo) * math.tan(math.radians(alpha))

    z_top_surface = z_surf(X_MAX)
    
    x_min_muro = min(x_bot_izq, x_top_izq)
    margen_lateral_izq = 2.2
    
    x_min_vista = x_min_muro - margen_lateral_izq
    x_max_vista = X_MAX + 4.5  
    
    ax.set_xlim(x_min_vista, x_max_vista)
    limite_superior = min(-1.5, z_top_surface - 1.5)
    if cargas and len(cargas) > 0:
        limite_superior -= 1.0 
    ax.set_ylim(H + 1.0, limite_superior)
    ax.set_aspect('equal')
    
    # 3. Dibujo de Estratos (Rellenos) y Lógica gamma (Saturado vs Seco)
    z_acc = 0.0
    colores = ['#e6ccb2', '#ddb892', '#b08968', '#7f5539', '#5c3a21']

    geometrias_estratos = []

    if len(estratos) == 0:
        # Dibujar un bloque gris base de advertencia si no hay estratos cargados
        pts_suelo = [[x_top_der, 0], [X_MAX, z_top_surface], [X_MAX, H], [x_bot_der, H]]
        suelo_vacio = patches.Polygon(pts_suelo, facecolor='#f0e6d2', alpha=0.5, edgecolor='black', linewidth=0.8, linestyle='--')
        ax.add_patch(suelo_vacio)
        ax.text((x_top_der + X_MAX)/2, H/2, "Sin estratos\ndefinidos", ha='center', va='center', color='gray', fontweight='bold')
    else:
        for i, est in enumerate(estratos):
            h_est = est.h
            z_bot = min(z_acc + h_est, H)
            color = colores[i % len(colores)]
            
            x_top_left = x_trasdos(z_acc)
            x_bot_left = x_trasdos(z_bot)
            
            if i == 0:
                pts_estrato = [[x_top_left, z_acc], [X_MAX, z_top_surface], [X_MAX, z_bot], [x_bot_left, z_bot]]
            else:
                pts_estrato = [[x_top_left, z_acc], [X_MAX, z_acc], [X_MAX, z_bot], [x_bot_left, z_bot]]
                
            pol_estrato = patches.Polygon(pts_estrato, facecolor=color, alpha=0.7, edgecolor='black', linewidth=0.8)
            ax.add_patch(pol_estrato)
            
            x_center = (max(x_top_left, x_bot_left) + X_MAX) / 2.0
            z_top_label = z_top_surface if i == 0 else z_acc
            
            # Evaluación del Nivel Freático (NF) para mostrar gamma o gamma_sat
            if nf_val is not None:
                if z_bot <= nf_val + 1e-5:
                    z_mid = (z_top_label + z_bot) / 2.0
                    etiqueta = f"Estrato {i+1}\nγ = {est.gamma}\nφ' = {est.phi}°\nc' = {est.cohesion}"
                    ax.text(x_center, z_mid, etiqueta, ha='center', va='center', fontsize=8, fontweight='bold', bbox=dict(facecolor='white', alpha=0.85, edgecolor='#cccccc', boxstyle='round,pad=0.3'))
                elif z_top_label >= nf_val - 1e-5:
                    z_mid = (z_top_label + z_bot) / 2.0
                    etiqueta = f"Estrato {i+1}\nγsat = {est.gamma_sat}\nφ' = {est.phi}°\nc' = {est.cohesion}"
                    ax.text(x_center, z_mid, etiqueta, ha='center', va='center', fontsize=8, fontweight='bold', bbox=dict(facecolor='white', alpha=0.85, edgecolor='#cccccc', boxstyle='round,pad=0.3'))
                else:
                    z_mid_above = (z_top_label + nf_val) / 2.0
                    etiqueta_above = f"Estrato {i+1}\nγ = {est.gamma}\nφ' = {est.phi}°\nc' = {est.cohesion}"
                    ax.text(x_center, z_mid_above, etiqueta_above, ha='center', va='center', fontsize=8, fontweight='bold', bbox=dict(facecolor='white', alpha=0.85, edgecolor='#cccccc', boxstyle='round,pad=0.3'))
                    
                    z_mid_below = (nf_val + z_bot) / 2.0
                    etiqueta_below = f"Estrato {i+1}\nγsat = {est.gamma_sat}\nφ' = {est.phi}°\nc' = {est.cohesion}"
                    ax.text(x_center, z_mid_below, etiqueta_below, ha='center', va='center', fontsize=8, fontweight='bold', bbox=dict(facecolor='white', alpha=0.85, edgecolor='#cccccc', boxstyle='round,pad=0.3'))
            else:
                z_mid = (z_top_label + z_bot) / 2.0
                etiqueta = f"Estrato {i+1}\nγ = {est.gamma}\nφ' = {est.phi}°\nc' = {est.cohesion}"
                ax.text(x_center, z_mid, etiqueta, ha='center', va='center', fontsize=8, fontweight='bold', bbox=dict(facecolor='white', alpha=0.85, edgecolor='#cccccc', boxstyle='round,pad=0.3'))
                
            geometrias_estratos.append((z_acc, z_bot, h_est))
            z_acc = z_bot
            if z_acc >= H: break

    # 4. Dibujar Bloques de Sobrecarga (Rojos)
    if cargas:
        for c in cargas:
            try:
                tipo = str(c[0]).lower()
                mag = float(c[1])
                a_dist = float(c[2])
                b_dist = float(c[3])
            except (ValueError, IndexError):
                continue

            if tipo == 'uniforme':
                x_start = x_inicio_suelo
                x_end = X_MAX
            elif tipo == 'franja':
                x_start = x_inicio_suelo + a_dist
                x_end = x_start + b_dist
            else:  
                x_start = x_inicio_suelo + a_dist
                x_end = x_start + 0.1  

            z1 = z_surf(x_start)
            z2 = z_surf(x_end)

            if tipo in ['uniforme', 'franja']:
                h_c = 0.6  
                pts_c = [[x_start, z1], [x_start, z1 - h_c], [x_end, z2 - h_c], [x_end, z2]]
                poly_c = patches.Polygon(pts_c, facecolor='#cc3333', alpha=0.6, edgecolor='darkred', lw=1.2)
                ax.add_patch(poly_c)
                ax.text((x_start + x_end) / 2, (z1 + z2) / 2 - h_c / 2, f"q={mag}", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
            else:
                ax.annotate('', xy=(x_start, z1), xytext=(x_start, z1 - 1.2), arrowprops=dict(arrowstyle='->', color='darkred', lw=2.5))
                ax.text(x_start, z1 - 1.4, f"Q={mag}", ha='center', va='bottom', color='darkred', fontsize=8, fontweight='bold')

    # 5. Dibujar el Agua (Nivel Freático)
    if nf_val is not None and nf_val < H:
        zw = nf_val
        x_agua_muro = x_trasdos(zw)
        ax.plot([x_agua_muro, X_MAX], [zw, zw], color='#0066cc', linestyle='--', linewidth=1.5)
        
        dy = max(0.2, H * 0.02)
        dx = max(0.1, H * 0.01)
        xt = X_MAX - dx * 10
        
        ax.plot([xt, xt-dx, xt+dx, xt], [zw, zw-dy, zw-dy, zw], color='#0066cc', lw=1.2)
        ax.plot([xt-dx*0.7, xt+dx*0.7], [zw+dy*0.3, zw+dy*0.3], color='#0066cc', lw=1.0)
        ax.plot([xt-dx*0.4, xt+dx*0.4], [zw+dy*0.6, zw+dy*0.6], color='#0066cc', lw=1.0)
        
        ax.text(xt + dx*2.0, zw - dy*0.3, f"NF (z = {zw}m)", color='#0066cc', fontsize=8, va='bottom', fontweight='bold', ha='left')

    # 6. Dibujar Dimensiones Dinámicas y Cotas (Líneas y Flechas Base)
    ax.plot([x_bot_der, x_bot_der + 1.2], [H, H], color='black', linestyle='--', lw=0.9)
    ax.text(x_bot_der + 0.2, H - 0.2, f"β = {beta_plot:.1f}°", color='blue', fontsize=8, fontweight='bold')

    ax.plot([x_inicio_suelo, x_inicio_suelo + 1.2], [0, 0], color='black', linestyle='--', lw=0.9)
    ax.text(x_inicio_suelo + 0.4, -0.2, f"α = {alpha}°", color='purple', fontsize=8, fontweight='bold')

    x_cota_h_izq = x_min_muro - 0.8
    ax.plot([x_cota_h_izq - 0.05, x_cota_h_izq + 0.05], [0, 0], color='black', lw=0.8)
    ax.plot([x_cota_h_izq - 0.05, x_cota_h_izq + 0.05], [H, H], color='black', lw=0.8)
    ax.annotate('', xy=(x_cota_h_izq, 0), xytext=(x_cota_h_izq, H), arrowprops=dict(arrowstyle='<->', color='black', lw=1))
    ax.text(x_cota_h_izq - 0.15, H / 2, f"H = {H:.1f} m", rotation=90, va='center', ha='right', fontsize=9, fontweight='bold')

    x_cota_parcial = X_MAX + 0.8    
    x_cota_total = X_MAX + 2.5      
    
    for z_acc, z_bot, h_est in geometrias_estratos:
        cortado_por_nf = (nf_val is not None) and (z_acc < nf_val < z_bot)
        
        if cortado_por_nf:
            h_seco = nf_val - z_acc
            ax.plot([x_cota_parcial - 0.1, x_cota_parcial + 0.1], [z_acc, z_acc], color='black', lw=0.8)
            ax.plot([x_cota_parcial - 0.1, x_cota_parcial + 0.1], [nf_val, nf_val], color='black', lw=0.8)
            ax.annotate('', xy=(x_cota_parcial, z_acc), xytext=(x_cota_parcial, nf_val), arrowprops=dict(arrowstyle='<->', color='#333333', lw=0.8))
            ax.text(x_cota_parcial, (z_acc + nf_val) / 2, f"{h_seco:.1f} m", va='center', ha='center', fontsize=8, bbox=dict(facecolor='white', edgecolor='none', pad=1))
            
            h_sum = z_bot - nf_val
            ax.plot([x_cota_parcial - 0.1, x_cota_parcial + 0.1], [nf_val, nf_val], color='black', lw=0.8)
            ax.plot([x_cota_parcial - 0.1, x_cota_parcial + 0.1], [z_bot, z_bot], color='black', lw=0.8)
            ax.annotate('', xy=(x_cota_parcial, nf_val), xytext=(x_cota_parcial, z_bot), arrowprops=dict(arrowstyle='<->', color='#333333', lw=0.8))
            ax.text(x_cota_parcial, (nf_val + z_bot) / 2, f"{h_sum:.1f} m", va='center', ha='center', fontsize=8, bbox=dict(facecolor='white', edgecolor='none', pad=1))
        
        ax.plot([x_cota_total - 0.1, x_cota_total + 0.1], [z_acc, z_acc], color='black', lw=0.8)
        ax.plot([x_cota_total - 0.1, x_cota_total + 0.1], [z_bot, z_bot], color='black', lw=0.8)
        ax.annotate('', xy=(x_cota_total, z_acc), xytext=(x_cota_total, z_bot), arrowprops=dict(arrowstyle='<->', color='black', lw=1))
        ax.text(x_cota_total, (z_acc + z_bot) / 2, f"{h_est:.1f} m", va='center', ha='center', fontsize=8, fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', pad=1))

    ax.set_title("Perfil Geotécnico y Estratigrafía", fontweight='bold', fontsize=10)


def renderizar_presiones(ax, resultado, factor_p=1.0, unidad_p="kN/m²"):
    """
    Motor de renderizado geométrico avanzado (Panel Derecho).
    Dibuja los esfuerzos proyectados y sesgados según el ángulo del relleno (alpha)
    y proyectados desde el muro (beta), imitando exactamente los esquemas de libros de texto.
    """
    ax.clear()
    if not resultado:
        ax.axis('off')
        return
    
    ax.axis('on')
    # Ocultar marcos sobrantes para un look científico limpio
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(False)
    
    filas = resultado.filas
    H = resultado.caso.altura
    beta = resultado.caso.beta
    
    # 1. Definir cara del muro (eje central referencial de las presiones)
    def x_muro(z_val):
        """Calcula el offset horizontal (x) de la cara del muro a la profundidad z provocado por beta."""
        if abs(beta - 90.0) < 1e-5: return 0.0
        return z_val / math.tan(math.radians(beta))
        
    z_muro_line = [0, H]
    x_muro_line = [x_muro(0), x_muro(H)]
    ax.plot(x_muro_line, z_muro_line, color='black', linewidth=1.5)
    
    def get_circle_num(num):
        """Devuelve el carácter especial numérico en círculo para enumerar las áreas."""
        if 1 <= num <= 20: return chr(0x245f + num)
        return f"({num})"
        
    area_idx = 1
    
    # 2. Lógica de Transformación Espacial (Sesgado Visual por Ángulo α de relleno)
    max_p = max(max(f.total * factor_p for f in filas), 1.0 * factor_p)
    max_x_bound = max_p * 1.25
    ratio_z_x = H / max_x_bound
    tan_t = math.tan(math.radians(resultado.caso.alpha))
    
    def transform(z_wall, p_val):
        """
        Función mágica que sesga la gráfica: Mapea una coordenada horizontal plana 
        a una proyectada oblicuamente aplicando trigonometría basada en alpha.
        """
        # x_final = Posición en el muro + Valor real de la presión
        # z_final = Profundidad real - Deformación geométrica por el ángulo alpha
        return x_muro(z_wall) + p_val, z_wall - (p_val * ratio_z_x) * tan_t

    def dibujar_fuerza(p_full, color_fill, color_line, is_water=False):
        """
        Dibuja un componente de esfuerzo dividiéndolo estricta e inteligentemente
        cada vez que cambia un estrato o toca el nivel freático.
        """
        nonlocal area_idx
        if max(p_full) < 1e-9: return False
        
        chunks = []
        chunk_z, chunk_p = [], []
        # Crear identificador único para "cortar" y segmentar la gráfica
        z_agua_eval = resultado.caso.z_agua if resultado.caso.z_agua is not None else 9999
        current_id = f"{filas[0].estrato}_{filas[0].z > z_agua_eval}"
        
        # Segmentar la lista gigante de resultados en bloques lógicos (Trapecios/Triángulos)
        for i, f in enumerate(filas):
            c_id = f"{f.estrato}_{f.z > z_agua_eval}"
            if c_id != current_id:
                chunks.append((chunk_z, chunk_p))
                chunk_z, chunk_p = [f.z], [p_full[i]]
                current_id = c_id
            else:
                chunk_z.append(f.z); chunk_p.append(p_full[i])
        if chunk_z: chunks.append((chunk_z, chunk_p))
        
        # Procesar cada bloque para dibujarlo y acotarlo
        for z_arr, p_arr in chunks:
            if max(p_arr) < 1e-9: continue
            
            # Construir el polígono sesgado dinámico usando la función Transform
            pts = [(x_muro(z), z) for z in z_arr] # Lado base (pegado al muro)
            pts += [transform(z, p) for z, p in zip(reversed(z_arr), reversed(p_arr))] # Lado externo oblicuo
            ax.add_patch(patches.Polygon(pts, facecolor=color_fill, alpha=0.9, edgecolor='none'))
            
            # Dibujar el contorno visible exterior
            out_x, out_z = [], []
            for z, p in zip(z_arr, p_arr):
                x_v, z_v = transform(z, p)
                out_x.append(x_v); out_z.append(z_v)
            
            l_style = '--' if is_water else '-'
            ax.plot(out_x, out_z, color=color_line, linestyle=l_style, linewidth=1.5)
            
            z_top, z_bot = z_arr[0], z_arr[-1]
            p_top, p_bot = p_arr[0], p_arr[-1]
            
            # Línea punteada que divide horizontalmente a los estratos
            if z_bot < H - 0.001:
                x1, z1 = x_muro(z_bot), z_bot
                x2, z2 = transform(z_bot, p_bot)
                ax.plot([x1, x2], [z1, z2], color='gray', linestyle=':', linewidth=1.2)
                
            # Imprimir los números reales de la presión en cada vértice del polígono
            xt, zt = transform(z_top, p_top)
            xb, zb = transform(z_bot, p_bot)
            if p_top > 0.01: ax.text(xt, zt, f" {p_top:.2f}", va='bottom', ha='left', fontsize=8)
            if p_bot > 0.01 and abs(p_bot - p_top) > 0.01: ax.text(xb, zb, f" {p_bot:.2f}", va='top', ha='left', fontsize=8)
                
            # Numeración circular inteligente para cada sub-área encontrada
            h_tramo = z_bot - z_top
            if h_tramo > 0.05:
                if abs(p_bot - p_top) > 0.01 and p_bot > 0.01 and p_top > 0.01:
                    # Forma Trapecial: Dibujar línea de corte paralela para dividir el rectángulo del triángulo base
                    min_p = min(p_top, p_bot)
                    x1, z1 = transform(z_top, min_p)
                    x2, z2 = transform(z_bot, min_p)
                    ax.plot([x1, x2], [z1, z2], color=color_line, linestyle='--', linewidth=0.8, alpha=0.7)
                    
                    xc, zc = transform(z_top + h_tramo/2, min_p/2)
                    ax.text(xc, zc, get_circle_num(area_idx), ha='center', va='center', fontsize=12, color=color_line)
                    area_idx += 1
                    
                    if p_bot > p_top: xc, zc = transform(z_top + h_tramo*(2/3), min_p + (p_bot - min_p)/3)
                    else: xc, zc = transform(z_top + h_tramo*(1/3), min_p + (p_top - min_p)/3)
                    ax.text(xc, zc, get_circle_num(area_idx), ha='center', va='center', fontsize=12, color=color_line)
                    area_idx += 1
                elif p_bot > 0.01 and p_top <= 0.01: # Solo Triángulo normal
                    xc, zc = transform(z_top + h_tramo*(2/3), p_bot/3)
                    ax.text(xc, zc, get_circle_num(area_idx), ha='center', va='center', fontsize=12, color=color_line)
                    area_idx += 1
                elif p_top > 0.01 and p_bot <= 0.01: # Solo Triángulo inverso
                    xc, zc = transform(z_top + h_tramo*(1/3), p_top/3)
                    ax.text(xc, zc, get_circle_num(area_idx), ha='center', va='center', fontsize=12, color=color_line)
                    area_idx += 1
                else: # Solo Rectángulo
                    xc, zc = transform(z_top + h_tramo/2, p_top/2)
                    ax.text(xc, zc, get_circle_num(area_idx), ha='center', va='center', fontsize=12, color=color_line)
                    area_idx += 1
        return True

    # 3. Mandar a construir todos los bloques superponiéndolos de forma segura y matemática
    has_suelo = dibujar_fuerza([f.suelo * factor_p for f in filas], '#eaf5ea', '#2ca02c')
    has_agua = dibujar_fuerza([f.agua * factor_p for f in filas], '#cce5ff', '#0066cc', is_water=True)
    has_carga = dibujar_fuerza([f.carga * factor_p for f in filas], '#ffe6cc', '#ff7f0e')
    has_sismo = dibujar_fuerza([f.sismo * factor_p for f in filas], '#ffeded', '#d62728')

    # 4. Construcción de Leyenda Personalizada
    custom_lines, labels = [], []
    if has_suelo:
        custom_lines.append(Line2D([0], [0], color='#2ca02c', lw=1.5, linestyle='-')); labels.append('Suelo')
    if has_agua:
        custom_lines.append(Line2D([0], [0], color='#0066cc', lw=1.5, linestyle='--')); labels.append('Agua')
    if has_carga:
        custom_lines.append(Line2D([0], [0], color='#ff7f0e', lw=1.5, linestyle='-')); labels.append('Sobrecargas')
    if has_sismo:
        custom_lines.append(Line2D([0], [0], color='#d62728', lw=1.5, linestyle='-')); labels.append('Sismo')
        
    ax.set_xlabel(f"Presión horizontal ({unidad_p})", fontsize=9)
    ax.set_ylabel("Profundidad z (m)", fontsize=9)
    ax.set_xticks([]) # Oculta numeración eje X por colisión visual
    
    if custom_lines: ax.legend(custom_lines, labels, loc="best", fontsize=8, framealpha=0.9, edgecolor='gray')
    ax.set_title("Esfuerzos Horizontales", fontweight='bold', fontsize=10)
    
    # 5. Ajustar dimensiones de visualización dinámicamente si el polígono sesgado se va muy arriba o a los lados
    min_z = min(-0.5, - H * abs(tan_t) * 1.5)
    ax.set_ylim(H + 0.5, min_z) # Invierte el eje de profundidades
    ax.set_xlim(min(0, -max_x_bound * 0.1), max_x_bound)