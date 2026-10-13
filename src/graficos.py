# Módulo de Gráficos Geotécnicos con Matplotlib.                                                     # [V.1.2.1]
# Renderiza el perfil físico del muro y los polígonos de presión resultantes.                         # [V.1.2.1]
# Mejoras V2: márgenes proporcionales a H, ejes que se ajustan a los textos, etiquetas sin            # [V.2.2.0]
# superposición, escala de presiones válida para cualquier unidad y gran flecha roja del empuje.     # [V.2.2.0]

import math                                                                                           # [V.1.1.0] Trigonometría y ángulos.
import matplotlib.patches as patches                                                                  # [V.1.1.0] Polígonos de muro, estratos y presiones.
import matplotlib.lines as mlines                                                                     # [V.1.2.1] Líneas de la leyenda (antes se importaba dentro de la función).
from matplotlib.patches import FancyArrowPatch                                                        # [V.2.2.0] Flechas con cabeza en puntos (no se deforman con la escala).


# =====================================================================================================
# [V.2.2.0] PALETA Y ESTILOS GLOBALES (aspecto de software comercial, un solo lugar para cambiarlos)
# =====================================================================================================
COLORES_ESTRATOS = ['#f1dfc1', '#e2c192', '#c99b6c', '#a6764b', '#7e5535', '#5f3e27']                 # [V.1.2.1] Tonos tierra de claro a oscuro.
COLOR_MURO = '#8c8f93'                                                                                # [V.2.2.0] Gris concreto.
BORDE_MURO = '#2b2b2b'                                                                                # [V.2.2.0] Borde del concreto.
COLOR_NF = '#1f6fd1'                                                                                  # [V.2.2.0] Azul del nivel freático.
COLOR_CARGA = '#c0392b'                                                                               # [V.2.2.0] Rojo de sobrecargas en el perfil.
COLOR_RESULTANTE = '#cc0000'                                                                          # [V.2.2.0] Rojo de la gran flecha del empuje.
COLORES_COMP = {'Suelo': '#2e8b3a', 'Agua': '#1f6fd1', 'Sobrecarga': '#e07b00', 'Sismo': '#c62828'}   # [V.1.2.1] Línea de cada componente.
RELLENOS_COMP = {'Suelo': '#e3f2e1', 'Agua': '#d6e8fb', 'Sobrecarga': '#ffecd2', 'Sismo': '#fde2e2'}  # [V.2.2.0] Relleno de cada componente.
CLAVE_COMPONENTE = {'Suelo': 'Suelo', 'Agua': 'Agua', 'Sobrecarga': 'Sobrecarga', 'Sismo': 'Incremento sísmico'}  # [V.2.2.0] Visibles -> claves de resultado.componentes.
CAJA_ETIQUETA = dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#b5b5b5', alpha=0.92, linewidth=0.6)  # [V.2.2.0] Caja de estratos.
CAJA_SIMPLE = dict(boxstyle='square,pad=0.15', facecolor='white', edgecolor='none', alpha=0.85)       # [V.2.2.0] Caja discreta de cotas/valores.


# =====================================================================================================
# [V.2.2.0] FUNCIONES AUXILIARES (privadas: empiezan con "_")
# =====================================================================================================
def _fmt(valor):                                                                                      # [V.2.2.0]
    """[V.2.2.0] Formatea un número con decimales adaptativos (sirve igual en kPa, MPa o t/m²)."""      # [V.2.2.0]
    a = abs(valor)                                                                                    # [V.2.2.0] Magnitud del valor.
    if a >= 100: return f"{valor:.1f}"                                                                # [V.2.2.0] Valores grandes: 1 decimal.
    if a >= 1: return f"{valor:.2f}"                                                                  # [V.2.2.0] Valores normales: 2 decimales.
    return f"{valor:.3f}"                                                                             # [V.2.2.0] Valores pequeños (ej. MPa): 3 decimales.


def _renderer(ax):                                                                                    # [V.2.2.0]
    """[V.2.2.0] Obtiene el renderizador para medir textos en píxeles (Tk, Agg o exportación)."""     # [V.2.2.0]
    try:                                                                                              # [V.2.2.0]
        canvas = ax.figure.canvas                                                                     # [V.2.2.0] Lienzo de la figura.
        if hasattr(canvas, 'get_renderer'): return canvas.get_renderer()                              # [V.2.2.0] TkAgg / Agg.
        return ax.figure._get_renderer()                                                              # [V.2.2.0] Respaldo para figuras sin lienzo.
    except Exception:                                                                                 # [V.2.2.0]
        return None                                                                                   # [V.2.2.0] Sin renderizador no se mide (el gráfico igual se dibuja).


def _fijar_limites(ax, x0, x1, z_sup, z_inf):                                                         # [V.2.2.0]
    """[V.2.2.0] Fija límites con el eje z invertido (profundidad positiva hacia abajo)."""           # [V.2.2.0]
    ax.set_xlim(min(x0, x1), max(x0, x1))                                                             # [V.2.2.0] Eje horizontal normal.
    ax.set_ylim(max(z_sup, z_inf), min(z_sup, z_inf))                                                 # [V.2.2.0] Eje vertical invertido.


def _expandir_limites_a_textos(ax, renderer, margen_px=6, iteraciones=4):                             # [V.2.2.0]
    """[V.2.2.0] Agranda los ejes lo justo para que NINGÚN texto quede cortado en los bordes."""      # [V.2.2.0]
    if renderer is None: return                                                                       # [V.2.2.0] Sin medición posible, se respeta lo calculado.
    for _ in range(iteraciones):                                                                      # [V.2.2.0] Se repite porque al agrandar con aspecto 1:1 cambia la escala.
        try: ax.apply_aspect()                                                                        # [V.2.2.0] Aplica el aspecto real antes de medir.
        except Exception: pass                                                                        # [V.2.2.0]
        inv = ax.transData.inverted()                                                                 # [V.2.2.0] Píxeles -> coordenadas de datos.
        x0, x1 = sorted(ax.get_xlim()); y0, y1 = sorted(ax.get_ylim())                                # [V.2.2.0] Límites actuales.
        nx0, nx1, ny0, ny1 = x0, x1, y0, y1                                                           # [V.2.2.0] Nuevos límites candidatos.
        for t in ax.texts:                                                                            # [V.2.2.0] Recorre textos y anotaciones del eje.
            if not t.get_visible() or not t.get_text().strip(): continue                              # [V.2.2.0] Ignora vacíos u ocultos.
            try: bb = t.get_window_extent(renderer).padded(margen_px)                                 # [V.2.2.0] Caja del texto en píxeles + margen.
            except Exception: continue                                                                # [V.2.2.0]
            (ax0, ay0), (ax1, ay1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])                  # [V.2.2.0] Caja en datos.
            nx0, nx1 = min(nx0, ax0, ax1), max(nx1, ax0, ax1)                                         # [V.2.2.0] Amplía en x.
            ny0, ny1 = min(ny0, ay0, ay1), max(ny1, ay0, ay1)                                         # [V.2.2.0] Amplía en z.
        tol = 1e-9 + 1e-4 * max(x1 - x0, y1 - y0)                                                     # [V.2.2.0] Tolerancia de convergencia.
        if nx0 > x0 - tol and nx1 < x1 + tol and ny0 > y0 - tol and ny1 < y1 + tol: break             # [V.2.2.0] Todo cabe: termina.
        _fijar_limites(ax, nx0, nx1, ny0, ny1)                                                        # [V.2.2.0] Aplica los límites ampliados.


def _evitar_solapes(ax, renderer, movibles, obstaculos=(), sep_px=2):                                 # [V.2.2.0]
    """[V.2.2.0] Desplaza verticalmente las etiquetas 'movibles' hasta que no choquen entre sí
    ni con los 'obstaculos' (leyenda, resultante, números de áreas)."""                               # [V.2.2.0]
    if renderer is None: return                                                                       # [V.2.2.0]
    ocupados = []                                                                                     # [V.2.2.0] Cajas ya colocadas (píxeles).
    for o in obstaculos:                                                                              # [V.2.2.0] Registra los obstáculos fijos.
        try: ocupados.append(o.get_window_extent(renderer))                                           # [V.2.2.0]
        except Exception: pass                                                                        # [V.2.2.0]
    for t in movibles:                                                                                # [V.2.2.0] Coloca etiquetas una por una.
        try: bb = t.get_window_extent(renderer)                                                       # [V.2.2.0] Caja actual.
        except Exception: continue                                                                    # [V.2.2.0]
        mejor = None                                                                                  # [V.2.2.0] (desplazamiento, caja) más corto.
        for sentido in (1, -1):                                                                       # [V.2.2.0] Prueba solo subir y solo bajar (no oscila).
            caja, dy_acum = bb, 0.0                                                                   # [V.2.2.0]
            for _ in range(200):                                                                      # [V.2.2.0] Tope de seguridad.
                choque = next((c for c in ocupados if caja.overlaps(c)), None)                        # [V.2.2.0] Primera caja que choca.
                if choque is None: break                                                              # [V.2.2.0] Libre.
                dy = (choque.y1 - caja.y0 + sep_px) if sentido > 0 else (choque.y0 - caja.y1 - sep_px)  # [V.2.2.0] Salta el obstáculo.
                caja = caja.translated(0, dy); dy_acum += dy                                          # [V.2.2.0]
            if mejor is None or abs(dy_acum) < abs(mejor[0]): mejor = (dy_acum, caja)                 # [V.2.2.0] Elige el más corto.
        dy_total, bb = mejor                                                                          # [V.2.2.0]
        if dy_total:                                                                                  # [V.2.2.0] Si hubo que moverla, mueve el texto real.
            trans = t.get_transform()                                                                 # [V.2.2.0] Transformación del texto.
            px, py = trans.transform(t.get_position())                                                # [V.2.2.0] Posición en píxeles.
            t.set_position(tuple(trans.inverted().transform((px, py + dy_total))))                    # [V.2.2.0] Nueva posición en datos.
        ocupados.append(bb)                                                                           # [V.2.2.0] Reserva su espacio.


def _colocar_leyenda(ax, renderer, handles, fijos, otros):                                            # [V.2.2.0]
    """[V.2.2.0] Prueba varias esquinas y deja la leyenda donde no tape la resultante y tape menos textos."""  # [V.2.2.0]
    if not handles: return None                                                                       # [V.2.2.0]
    opciones = ['upper right', 'lower right', 'upper left', 'lower left', 'center right']              # [V.2.2.0] Orden de preferencia.
    if renderer is None: return ax.legend(handles=handles, loc=opciones[0], fontsize=8, framealpha=0.92)  # [V.2.2.0]
    def cajas(lista):                                                                                 # [V.2.2.0]
        out = []                                                                                      # [V.2.2.0]
        for t in lista:                                                                               # [V.2.2.0]
            try: out.append(t.get_window_extent(renderer))                                            # [V.2.2.0]
            except Exception: pass                                                                    # [V.2.2.0]
        return out                                                                                    # [V.2.2.0]
    c_fijos, c_otros = cajas(fijos), cajas(otros)                                                     # [V.2.2.0]
    mejor, mejor_costo = opciones[0], None                                                            # [V.2.2.0]
    for loc in opciones:                                                                              # [V.2.2.0]
        leg = ax.legend(handles=handles, loc=loc, fontsize=8, framealpha=0.92)                        # [V.2.2.0]
        bb = leg.get_window_extent(renderer)                                                          # [V.2.2.0]
        costo = 1000 * sum(bb.overlaps(c) for c in c_fijos) + sum(bb.overlaps(c) for c in c_otros)   # [V.2.2.0] Tapar la resultante pesa mucho.
        if mejor_costo is None or costo < mejor_costo: mejor, mejor_costo = loc, costo                # [V.2.2.0]
        if costo == 0: break                                                                          # [V.2.2.0] Esquina libre encontrada.
    return ax.legend(handles=handles, loc=mejor, fontsize=8, framealpha=0.92)                         # [V.2.2.0]


def _cota_vertical(ax, x, z1, z2, texto, tick, color='black', lw=0.9, negrita=False, ha='center', dx_texto=0.0):  # [V.2.2.0]
    """[V.2.2.0] Dibuja una cota vertical con topes y flecha doble; devuelve el texto creado."""      # [V.2.2.0]
    ax.plot([x - tick, x + tick], [z1, z1], color=color, lw=0.8)                                      # [V.2.2.0] Tope superior.
    ax.plot([x - tick, x + tick], [z2, z2], color=color, lw=0.8)                                      # [V.2.2.0] Tope inferior.
    ax.annotate('', xy=(x, z1), xytext=(x, z2), arrowprops=dict(arrowstyle='<->', color=color, lw=lw, shrinkA=0, shrinkB=0))  # [V.2.2.0] Flecha doble.
    return ax.text(x + dx_texto, (z1 + z2) / 2.0, texto, va='center', ha=ha, fontsize=8,              # [V.2.2.0] Texto de la cota.
                   fontweight='bold' if negrita else 'normal', color=color, bbox=CAJA_SIMPLE, zorder=6)  # [V.2.2.0]


def _cota_horizontal(ax, z, x1, x2, texto, tick, color='black'):                                      # [V.2.2.0]
    """[V.2.2.0] Dibuja una cota horizontal con topes; devuelve el texto creado."""                   # [V.2.2.0]
    ax.plot([x1, x1], [z - tick, z + tick], color=color, lw=0.8)                                      # [V.2.2.0] Tope izquierdo.
    ax.plot([x2, x2], [z - tick, z + tick], color=color, lw=0.8)                                      # [V.2.2.0] Tope derecho.
    ax.annotate('', xy=(x1, z), xytext=(x2, z), arrowprops=dict(arrowstyle='<->', color=color, lw=0.9, shrinkA=0, shrinkB=0))  # [V.2.2.0]
    return ax.text((x1 + x2) / 2.0, z, texto, ha='center', va='center', fontsize=8, color=color, bbox=CAJA_SIMPLE, zorder=6)  # [V.2.2.0]


def _arco(ax, cx, cz, r, ang_ini, ang_fin, color):                                                    # [V.2.2.0]
    """[V.2.2.0] Arco de ángulo en coordenadas de datos (0° = +x, ángulos positivos hacia arriba)."""  # [V.2.2.0]
    n = 24                                                                                            # [V.2.2.0] Resolución del arco.
    angs = [math.radians(ang_ini + (ang_fin - ang_ini) * i / n) for i in range(n + 1)]                # [V.2.2.0]
    ax.plot([cx + r * math.cos(a) for a in angs], [cz - r * math.sin(a) for a in angs], color=color, lw=1.0, zorder=7)  # [V.2.2.0] z crece hacia abajo.


# =====================================================================================================
# PERFIL GEOTÉCNICO
# =====================================================================================================
def renderizar_perfil(ax, altura, estratos, cargas=None, nf_val=None, alpha=0.0, beta=90.0, tipo_muro="Rectangular", modo_muro="Genérico", b_base=2.0, e_pantalla=0.5, unidad_L="m"):  # [V.1.1.0] Firma sin cambios (compatibilidad con interfaz.py).
    """
    [V.1.2.1] Dibuja el muro, los estratos coloreados, sobrecargas, nivel freático y todas las cotas.
    Todos los márgenes y tamaños son proporcionales a H, así que se ve bien con H = 1 m o H = 30 m.
    """
    ax.clear(); ax.axis('off')                                                                        # [V.1.1.0] Limpia el lienzo y oculta ejes cartesianos.
    try: H = float(altura)                                                                            # [V.2.2.0] Asegura un número.
    except (TypeError, ValueError): H = 0.0                                                           # [V.2.2.0]
    if H <= 0:                                                                                        # [V.1.2.1] Altura inválida: aviso en vez de lienzo vacío.
        ax.text(0.5, 0.5, "Ingrese una altura H > 0 para dibujar el muro", transform=ax.transAxes,    # [V.2.2.0]
                ha='center', va='center', color='gray', fontsize=10)                                  # [V.2.2.0]
        return                                                                                        # [V.1.1.0]

    u = 0.05 * H                                                                                      # [V.2.2.0] "Unidad gráfica": todos los márgenes escalan con H.
    tick = 0.25 * u                                                                                   # [V.2.2.0] Tamaño de los topes de cota.

    beta_plot = 89.0 if (tipo_muro == "Trapezoidal" and beta >= 90.0) else beta                       # [V.1.1.0] Limita β del trapecio.

    def x_desplazamiento(z_val):                                                                      # [V.1.1.0]
        """[V.1.1.0] Desplazamiento horizontal de la cara por la inclinación β."""                    # [V.1.1.0]
        if abs(beta_plot - 90.0) < 1e-5: return 0.0                                                   # [V.1.1.0] Cara vertical.
        return - (H - z_val) / math.tan(math.radians(beta_plot))                                      # [V.1.1.0]

    desp_corona = x_desplazamiento(0.0)                                                               # [V.1.1.0] Desplazamiento en la corona.

    # [V.1.1.0] Vértices del muro según tipología (geometría original, sin cambios).
    if tipo_muro == "Trapezoidal":                                                                    # [V.1.1.0]
        b, e = b_base, e_pantalla                                                                     # [V.1.1.0]
        if modo_muro == "Personalizado":                                                              # [V.1.1.0]
            if b <= e: b = e + 0.1                                                                    # [V.1.1.0]
            beta_plot = math.degrees(math.atan2(H, (b - e) / 2.0))                                    # [V.1.1.0]
        else:                                                                                         # [V.1.1.0]
            e = 0.5; b = max(e + 0.1, e - 2 * desp_corona)                                            # [V.1.1.0]
        center = b / 2.0                                                                              # [V.1.1.0]
        x_bot_izq, x_bot_der = center - b / 2.0, center + b / 2.0                                     # [V.1.1.0]
        x_top_izq, x_top_der = center - e / 2.0, center + e / 2.0                                     # [V.1.1.0]
    else:                                                                                             # [V.1.1.0]
        b = b_base if modo_muro == "Personalizado" else 0.5                                           # [V.1.1.0]
        e = b                                                                                         # [V.2.2.0] Corona = base en el rectangular (para la cota).
        x_bot_izq, x_bot_der = 0.0, b                                                                 # [V.1.1.0]
        x_top_izq, x_top_der = x_bot_izq + desp_corona, x_bot_der + desp_corona                       # [V.1.1.0]

    pts_muro = [[x_top_izq, 0], [x_top_der, 0], [x_bot_der, H], [x_bot_izq, H]]                       # [V.1.1.0] Polígono del muro.
    ax.add_patch(patches.Polygon(pts_muro, facecolor=COLOR_MURO, edgecolor=BORDE_MURO, linewidth=1.6, # [V.1.2.1] Concreto gris claro.
                                 hatch='..', zorder=4))                                               # [V.2.2.0] Textura tipo concreto.

    def x_trasdos(z_val): return x_top_der + (x_bot_der - x_top_der) * (z_val / H)                    # [V.1.1.0] Cara posterior en función de z.
    # [V.2.2.0] Largo del relleno dinámico: se alarga para llenar el ancho del panel (antes 2H fijo),
    # así el muro no se ve diminuto en la ventana. Se limita entre 1.5H y 4H.
    try: Rw = ax.bbox.width / max(ax.bbox.height, 1.0)                                                # [V.2.2.0] Proporción ancho/alto del panel.
    except Exception: Rw = 2.5                                                                        # [V.2.2.0]
    t_a = max(0.0, math.tan(math.radians(alpha)))                                                     # [V.2.2.0] Subida del relleno por metro.
    c_fijo = (max(x_bot_der, x_top_der) - min(x_bot_izq, x_top_izq)) + 14 * u                       # [V.2.2.0] Muro + cotas izquierda/derecha.
    den = 1.0 - 0.8 * Rw * t_a                                                                        # [V.2.2.0]
    L_rell = (0.8 * Rw * 1.3 * H - c_fijo) / den if den > 0.05 else 1.5 * H                           # [V.2.2.0] Ancho que llena el panel (0.8 = holgura).
    L_rell = min(max(L_rell, 1.5 * H), 4.0 * H)                                                       # [V.2.2.0]
    X_MAX = max(x_bot_der, x_top_der) + L_rell                                                        # [V.1.2.1] Extensión del relleno.
    def z_surf(x_val): return - (x_val - x_top_der) * math.tan(math.radians(alpha))                   # [V.1.1.0] Superficie inclinada α.

    x_min_muro = min(x_bot_izq, x_top_izq)                                                            # [V.2.2.0] Borde izquierdo del muro.
    z_sup_terreno = min(0.0, z_surf(X_MAX))                                                           # [V.2.2.0] Punto más alto del relleno.

    # [V.2.2.0] Límites preliminares (se afinan al final según los textos) para estimar la escala en píxeles.
    _fijar_limites(ax, x_min_muro - 4 * u, X_MAX + 8 * u, z_sup_terreno - 4 * u, H + 3 * u)           # [V.2.2.0]
    ax.set_aspect('equal')                                                                            # [V.1.1.0] Proporción real 1:1.
    try:                                                                                              # [V.2.2.0] Píxeles por unidad de longitud (para decidir tamaño de etiquetas).
        x0, x1 = ax.get_xlim(); y1, y0 = ax.get_ylim()                                                # [V.2.2.0]
        px_por_m = 0.85 * min(ax.bbox.width / abs(x1 - x0), ax.bbox.height / abs(y1 - y0))            # [V.2.2.0] 0.85 = margen por el ajuste final.
    except Exception:                                                                                 # [V.2.2.0]
        px_por_m = 1e9                                                                                # [V.2.2.0] Si no se puede medir, etiqueta completa.

    def etiqueta_estrato(i, est, saturado, h_disp):                                                   # [V.2.2.0]
        """[V.2.2.0] Texto del estrato; se compacta si el estrato es delgado en pantalla."""          # [V.2.2.0]
        g = f"γsat = {est.gamma_sat}" if saturado else f"γ = {est.gamma}"                             # [V.2.2.0] Peso específico según NF.
        alto_px = h_disp * px_por_m                                                                   # [V.2.2.0] Alto disponible en píxeles.
        if alto_px >= 58: return f"Estrato {i+1}\n{g}\nφ' = {est.phi}°\nc' = {est.cohesion}"          # [V.1.2.1] Etiqueta completa (formato original).
        if alto_px >= 16: return f"E{i+1}: {g} · φ' = {est.phi}° · c' = {est.cohesion}"               # [V.2.2.0] Una sola línea.
        return f"E{i+1}"                                                                              # [V.2.2.0] Estrato muy delgado.

    textos_movibles = []                                                                              # [V.2.2.0] Etiquetas que pueden reubicarse si chocan.
    geometrias_estratos = []                                                                          # [V.1.1.0] (z_ini, z_fin, espesor) para cotas.
    z_acc = 0.0                                                                                       # [V.1.1.0] Profundidad acumulada.

    if not estratos:                                                                                  # [V.1.1.0] Sin estratos: relleno genérico.
        pts = [[x_top_der, 0], [X_MAX, z_surf(X_MAX)], [X_MAX, H], [x_bot_der, H]]                    # [V.1.1.0]
        ax.add_patch(patches.Polygon(pts, facecolor='#f0e6d2', alpha=0.5, edgecolor='black', linestyle='--', zorder=1))  # [V.1.1.0]
        ax.text((x_top_der + X_MAX) / 2, H / 2, "Sin estratos", ha='center', va='center', color='gray', fontweight='bold')  # [V.1.1.0]
    else:                                                                                             # [V.1.1.0]
        for i, est in enumerate(estratos):                                                            # [V.1.1.0] Recorre estratos de arriba hacia abajo.
            if est.h <= 0: continue                                                                   # [V.2.2.0] Ignora espesores nulos/negativos.
            z_bot = min(z_acc + est.h, H)                                                             # [V.1.1.0] Recorta en la base del muro.
            x_top_left, x_bot_left = x_trasdos(z_acc), x_trasdos(z_bot)                               # [V.1.1.0]
            z_top_der = z_surf(X_MAX) if i == 0 else z_acc                                            # [V.1.2.1] El primero sigue la pendiente α.
            pts = [[x_top_left, z_acc], [X_MAX, z_top_der], [X_MAX, z_bot], [x_bot_left, z_bot]]      # [V.1.1.0]
            ax.add_patch(patches.Polygon(pts, facecolor=COLORES_ESTRATOS[i % len(COLORES_ESTRATOS)],  # [V.1.2.1] Color por estrato.
                                         alpha=0.9, edgecolor='#5a4632', linewidth=0.9, zorder=1))    # [V.1.2.1]
            xc = (max(x_top_left, x_bot_left) + X_MAX) / 2.0                                          # [V.1.1.0] Centro horizontal de la etiqueta.

            # [V.1.2.1] Si el NF corta el estrato se ponen dos etiquetas (γ arriba, γsat abajo).
            if nf_val is not None and z_top_der < nf_val - 1e-5 and z_bot > nf_val + 1e-5:            # [V.1.2.1] NF dentro del estrato.
                tramos = [(z_top_der, nf_val, False), (nf_val, z_bot, True)]                          # [V.1.2.1]
            else:                                                                                     # [V.1.2.1]
                sat = nf_val is not None and z_top_der >= nf_val - 1e-5                               # [V.1.2.1] Totalmente bajo el NF.
                tramos = [(z_top_der, z_bot, sat)]                                                    # [V.1.2.1]
            for za, zb, sat in tramos:                                                                # [V.2.2.0]
                t = ax.text(xc, (za + zb) / 2.0, etiqueta_estrato(i, est, sat, zb - max(za, z_acc)), # [V.1.2.1]
                            ha='center', va='center', fontsize=8, bbox=CAJA_ETIQUETA, zorder=5)       # [V.1.2.1]
                textos_movibles.append(t)                                                             # [V.2.2.0]

            geometrias_estratos.append((z_acc, z_bot, z_bot - z_acc))                                 # [V.1.2.1] Espesor real dibujado.
            z_acc = z_bot                                                                             # [V.1.1.0]
            if z_acc >= H: break                                                                      # [V.1.1.0]

        if z_acc < H - 1e-6:                                                                          # [V.2.2.0] Los estratos no llegan a la base: se avisa.
            pts = [[x_trasdos(z_acc), z_acc], [X_MAX, z_acc], [X_MAX, H], [x_bot_der, H]]             # [V.2.2.0]
            ax.add_patch(patches.Polygon(pts, facecolor='white', edgecolor='#999999', hatch='//',     # [V.2.2.0]
                                         linestyle='--', linewidth=0.8, zorder=1))                    # [V.2.2.0]
            t = ax.text((x_trasdos(z_acc) + X_MAX) / 2, (z_acc + H) / 2, "Sin datos de estrato",      # [V.2.2.0]
                        ha='center', va='center', fontsize=8, color='#777777', bbox=CAJA_SIMPLE, zorder=5)  # [V.2.2.0]
            textos_movibles.append(t)                                                                 # [V.2.2.0]

    # [V.2.2.0] Línea de superficie del relleno y línea de terreno al pie del muro.
    ax.plot([x_top_der, X_MAX], [0.0, z_surf(X_MAX)], color='#4a3626', lw=1.6, zorder=3)              # [V.2.2.0]
    ax.plot([x_min_muro - 3 * u, X_MAX], [H, H], color='#4a3626', lw=1.6, zorder=3)       # [V.2.2.0]
    for k in range(10):                                                                               # [V.2.2.0] Rayado de terreno natural bajo la base.
        xk = x_min_muro - 3 * u + k * (X_MAX - x_min_muro + 3 * u) / 10.0                             # [V.2.2.0]
        ax.plot([xk, xk - 0.6 * u], [H, H + 0.6 * u], color='#4a3626', lw=0.7, zorder=3)              # [V.2.2.0]

    # [V.1.2.1] Sobrecargas sobre la superficie del terreno (tamaños proporcionales a H).
    if cargas:                                                                                        # [V.1.1.0]
        for c in cargas:                                                                              # [V.1.1.0]
            try: tipo, mag, a_dist, b_dist = str(c[0]).strip().lower(), float(c[1]), float(c[2]), float(c[3])  # [V.1.1.0]
            except (ValueError, IndexError, TypeError): continue                                      # [V.1.2.1]
            x_start = x_top_der if tipo == 'uniforme' else x_top_der + a_dist                         # [V.1.1.0]
            x_end = X_MAX if tipo == 'uniforme' else (x_start + b_dist if tipo == 'franja' else x_start)  # [V.1.2.1]
            z1, z2 = z_surf(x_start), z_surf(x_end)                                                   # [V.1.1.0]
            if tipo in ['uniforme', 'franja']:                                                        # [V.1.1.0] Bloque de presión.
                h_c = 1.2 * u                                                                         # [V.1.2.1] Alto proporcional (antes 0.6 m fijo).
                ax.add_patch(patches.Polygon([[x_start, z1], [x_start, z1 - h_c], [x_end, z2 - h_c], [x_end, z2]],  # [V.1.1.0]
                                             facecolor=COLOR_CARGA, alpha=0.65, edgecolor='darkred', zorder=4))   # [V.1.2.1]
                n_fl = max(2, int(abs(x_end - x_start) / (2.5 * u)))                                  # [V.2.2.0] Flechitas de la carga repartida.
                for k in range(n_fl + 1):                                                             # [V.2.2.0]
                    xk = x_start + (x_end - x_start) * k / n_fl                                       # [V.2.2.0]
                    zk = z_surf(xk)                                                                   # [V.2.2.0]
                    ax.annotate('', xy=(xk, zk), xytext=(xk, zk - h_c), arrowprops=dict(arrowstyle='->', color='darkred', lw=0.8), zorder=5)  # [V.2.2.0]
                t = ax.text((x_start + x_end) / 2, (z1 + z2) / 2 - h_c - 0.3 * u, f"q = {mag}",       # [V.1.2.1] Texto encima del bloque.
                            ha='center', va='bottom', color='darkred', fontsize=8, fontweight='bold', bbox=CAJA_SIMPLE, zorder=6)  # [V.1.2.1]
            else:                                                                                     # [V.1.1.0] Lineal / puntual.
                ax.annotate('', xy=(x_start, z1), xytext=(x_start, z1 - 3 * u),                       # [V.1.2.1]
                            arrowprops=dict(arrowstyle='-|>', color='darkred', lw=2.0, mutation_scale=12), zorder=5)  # [V.1.2.1]
                t = ax.text(x_start, z1 - 3.2 * u, f"Q = {mag}", ha='center', va='bottom', color='darkred',  # [V.1.2.1]
                            fontsize=8, fontweight='bold', bbox=CAJA_SIMPLE, zorder=6)                # [V.1.2.1]
            textos_movibles.append(t)                                                                 # [V.2.2.0]

    # [V.1.2.1] Nivel freático: línea, zona saturada y símbolo ▽.
    if nf_val is not None and 0 <= nf_val < H:                                                        # [V.1.2.1]
        zw = nf_val                                                                                   # [V.1.1.0]
        ax.add_patch(patches.Polygon([[x_trasdos(zw), zw], [X_MAX, zw], [X_MAX, H], [x_bot_der, H]],  # [V.2.2.0] Zona saturada en azul suave.
                                     facecolor=COLOR_NF, alpha=0.10, edgecolor='none', zorder=2))     # [V.2.2.0]
        ax.plot([x_trasdos(zw), X_MAX], [zw, zw], color=COLOR_NF, linestyle='--', linewidth=1.5, zorder=3)  # [V.1.1.0]
        xt = X_MAX - 2.0 * u                                                                          # [V.1.2.1] Posición del símbolo.
        ax.plot([xt, xt - 0.5 * u, xt + 0.5 * u, xt], [zw, zw - 0.8 * u, zw - 0.8 * u, zw], color=COLOR_NF, lw=1.2, zorder=6)  # [V.1.2.1] ▽
        t = ax.text(xt - 0.8 * u, zw - 0.3 * u, f"NF (z = {zw} {unidad_L})", color=COLOR_NF, fontsize=8,  # [V.1.2.1]
                    va='bottom', ha='right', fontweight='bold', bbox=CAJA_SIMPLE, zorder=6)           # [V.1.2.1]
        textos_movibles.append(t)                                                                     # [V.2.2.0]

    # [V.1.2.1] Ángulo β en la base del trasdós (medido desde la horizontal, lado del muro) con arco.
    ang_cara = math.degrees(math.atan2(H, x_bot_der - x_top_der))                                     # [V.2.2.0] Ángulo real de la cara dibujada.
    r_arc = 1.6 * u                                                                                   # [V.2.2.0] Radio del arco.
    ax.plot([x_bot_der, x_bot_der - 2.2 * u], [H, H], color='#f5d300', linestyle='--', lw=0.9, zorder=7)  # [V.1.2.1] Referencia horizontal.
    _arco(ax, x_bot_der, H, r_arc, 180.0 - ang_cara, 180.0, '#f5d300')   # [V.2.2.0] Arco β (amarillo, visible sobre el concreto).
    t = ax.text(x_bot_der + 0.4 * u, H - 1.0 * u, f"β = {beta_plot:.1f}°", color='#1a4fb5', fontsize=8,  # [V.1.2.1]
                fontweight='bold', ha='left', va='bottom', bbox=CAJA_SIMPLE, zorder=8)                # [V.1.2.1]
    textos_movibles.append(t)                                                                         # [V.2.2.0]

    # [V.1.2.1] Ángulo α del relleno en la corona.
    ax.plot([x_top_der, x_top_der + 3 * u], [0, 0], color='black', linestyle='--', lw=0.9, zorder=7)  # [V.1.1.0]
    if abs(alpha) > 1e-6: _arco(ax, x_top_der, 0.0, 2.4 * u, 0.0, float(alpha), '#7b2fa8')           # [V.2.2.0] Arco α.
    t = ax.text(x_top_der + 3.2 * u, -0.2 * u, f"α = {alpha}°", color='#7b2fa8', fontsize=8,          # [V.1.2.1]
                fontweight='bold', ha='left', va='bottom', bbox=CAJA_SIMPLE, zorder=8)                # [V.1.2.1]
    textos_movibles.append(t)                                                                         # [V.2.2.0]

    # [V.1.2.1] Cota de altura total H (izquierda).
    x_cota_h = x_min_muro - 2.0 * u                                                                   # [V.1.2.1]
    ax.plot([x_cota_h, x_min_muro], [0, 0], color='#888888', lw=0.6, ls=':')                          # [V.2.2.0] Línea de referencia corona.
    t_H = _cota_vertical(ax, x_cota_h, 0.0, H, f"H = {H:.2f} {unidad_L}", tick, negrita=True)         # [V.1.2.1]
    t_H.set_rotation(90)                                                                              # [V.1.1.0] Texto vertical.

    # [V.2.2.0] Cotas de ancho de base y corona del muro.
    t_b = _cota_horizontal(ax, H + 2.0 * u, x_bot_izq, x_bot_der, f"b = {x_bot_der - x_bot_izq:.2f} {unidad_L}", tick)  # [V.2.2.0]
    textos_cota = [t_b]                                                                               # [V.2.2.0]
    if tipo_muro == "Trapezoidal":                                                                    # [V.2.2.0] En trapecio la corona difiere de la base.
        textos_cota.append(_cota_horizontal(ax, -1.8 * u, x_top_izq, x_top_der, f"e = {x_top_der - x_top_izq:.2f} {unidad_L}", tick))  # [V.2.2.0]

    # [V.1.2.1] Cotas de estratos a la derecha: columna parcial (NF) y columna total.
    x_cota_parcial = X_MAX + 1.0 * u                                                                  # [V.1.2.1]
    textos_parciales = []                                                                             # [V.2.2.0]
    hay_parcial = False                                                                               # [V.2.2.0]
    for z_a, z_b, h_e in geometrias_estratos:                                                         # [V.1.1.0]
        if nf_val is not None and z_a < nf_val < z_b:                                                 # [V.1.1.0] Estrato partido por el NF.
            hay_parcial = True                                                                        # [V.2.2.0]
            textos_parciales.append(_cota_vertical(ax, x_cota_parcial, z_a, nf_val, f"{nf_val - z_a:.2f} {unidad_L}", tick, color='#1f4e8c', ha='left', dx_texto=0.4 * u))  # [V.1.2.1]
            textos_parciales.append(_cota_vertical(ax, x_cota_parcial, nf_val, z_b, f"{z_b - nf_val:.2f} {unidad_L}", tick, color='#1f4e8c', ha='left', dx_texto=0.4 * u))  # [V.1.2.1]

    # [V.2.2.0] La columna total se coloca después de medir el ancho real de los textos parciales (no se pisan).
    x_cota_total = X_MAX + (1.0 if not hay_parcial else 3.5) * u                                      # [V.2.2.0] Posición base.
    rend = _renderer(ax)                                                                              # [V.2.2.0]
    if hay_parcial and rend is not None:                                                              # [V.2.2.0]
        try:                                                                                          # [V.2.2.0]
            inv = ax.transData.inverted()                                                             # [V.2.2.0]
            borde = max(inv.transform((t.get_window_extent(rend).x1, 0))[0] for t in textos_parciales)  # [V.2.2.0] Borde derecho de parciales.
            x_cota_total = max(x_cota_total, borde + 1.0 * u)                                         # [V.2.2.0]
        except Exception: pass                                                                        # [V.2.2.0]
    for z_a, z_b, h_e in geometrias_estratos:                                                         # [V.1.1.0]
        ax.plot([X_MAX, x_cota_total], [z_a, z_a], color='#888888', lw=0.5, ls=':')                   # [V.2.2.0] Línea de referencia.
        textos_cota.append(_cota_vertical(ax, x_cota_total, z_a, z_b, f"{h_e:.2f} {unidad_L}", tick, negrita=True, ha='left', dx_texto=0.4 * u))  # [V.1.2.1]
    if geometrias_estratos:                                                                           # [V.2.2.0]
        ax.plot([X_MAX, x_cota_total], [geometrias_estratos[-1][1]] * 2, color='#888888', lw=0.5, ls=':')  # [V.2.2.0] Cierre inferior.

    ax.set_title("Perfil Geotécnico y Estratigrafía", fontweight='bold', fontsize=10)                 # [V.1.1.0]

    # [V.2.2.0] Ajuste final: límites a la medida del dibujo + reubicación de textos que chocan.
    _fijar_limites(ax, x_cota_h - 1.5 * u, x_cota_total + 1.5 * u, z_sup_terreno - 2 * u, H + 3 * u)  # [V.2.2.0]
    _expandir_limites_a_textos(ax, rend)                                                              # [V.2.2.0]
    for _ in range(2):                                                                                # [V.2.2.0] 2 pasadas por el reajuste de escala.
        _evitar_solapes(ax, rend, textos_parciales + textos_movibles, obstaculos=textos_cota + [t_H]) # [V.2.2.0]
        _expandir_limites_a_textos(ax, rend)                                                          # [V.2.2.0] Por si alguna etiqueta se movió al borde.


# =====================================================================================================
# DIAGRAMA DE PRESIONES
# =====================================================================================================
def renderizar_presiones(ax, resultado, scale_z=1.0, scale_p=1.0, unidad_p="kPa", unidad_z="m", scale_F=1.0, unidad_F="kN/m", visibles=None, titulo_custom="Esfuerzos Horizontales Analíticos"):  # [V.1.1.0] Firma sin cambios.
    """
    [V.1.2.1] Dibuja los polígonos de presión (Suelo, Agua, Sobrecargas, Sismo), los vectores parciales
    y la gran flecha roja del empuje resultante. Ejes dinámicos y etiquetas sin superponerse.
    """
    vis = {'Suelo': True, 'Agua': True, 'Sobrecarga': True, 'Sismo': True, 'Vectores': True}         # [V.1.2.1] Valores por defecto.
    if visibles: vis.update(visibles)                                                                 # [V.2.2.0] Acepta diccionarios incompletos sin KeyError.

    ax.clear(); ax.axis('on')                                                                         # [V.1.1.0]
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.grid(False)        # [V.1.1.0]
    if not resultado or not resultado.filas:                                                          # [V.1.2.1] Sin resultados: aviso.
        ax.axis('off')                                                                                # [V.2.2.0]
        ax.text(0.5, 0.5, "Presione «Calcular» para ver los esfuerzos", transform=ax.transAxes, ha='center', va='center', color='gray')  # [V.2.2.0]
        return                                                                                        # [V.1.1.0]

    H_disp = resultado.caso.altura * scale_z                                                          # [V.1.1.0] Altura en unidades de pantalla.
    beta = resultado.caso.beta                                                                        # [V.1.1.0]
    tan_t = math.tan(math.radians(resultado.caso.alpha))                                              # [V.1.1.0]

    # [V.1.2.1] Escala dinámica: se mide el MAYOR polígono individual visible (se dibujan superpuestos,
    # no apilados), y ya no se fuerza un mínimo de 1.0 (eso aplastaba los gráficos en MPa).
    campos = {'Suelo': 'suelo', 'Agua': 'agua', 'Sobrecarga': 'carga', 'Sismo': 'sismo'}             # [V.2.2.0]
    valores = [getattr(f, campo) * scale_p for comp, campo in campos.items() if vis.get(comp) for f in resultado.filas]  # [V.2.2.0]
    min_p_vis = min(valores + [0.0])                                                                  # [V.1.2.1]
    max_p_vis = max(valores + [0.0])                                                                  # [V.1.2.1]
    span_p = max_p_vis - min_p_vis                                                                    # [V.1.2.1]
    if span_p <= 1e-12: span_p = 1.0                                                                  # [V.2.2.0] Solo si todo es cero.
    ratio_z_x = H_disp / span_p                                                                       # [V.1.1.0]
    umbral_p = 0.005 * span_p                                                                         # [V.2.2.0] Umbral relativo (antes 0.1 absoluto).

    def x_muro(z_disp):                                                                               # [V.1.2.1]
        """[V.1.2.1] Cara del muro en el eje de presiones. Se convierte la inclinación (longitud) a
        unidades de presión con 1/ratio_z_x; antes se sumaban metros a kPa y en MPa el diagrama se aplastaba."""  # [V.2.2.0]
        if abs(beta - 90.0) < 1e-5: return 0.0                                                        # [V.1.1.0]
        return (z_disp / math.tan(math.radians(beta))) / ratio_z_x                                    # [V.1.2.1]

    def transform(z_disp, p_scaled):                                                                  # [V.1.1.0]
        """[V.1.1.0] Inclina el diagrama según la pendiente del terreno."""                           # [V.1.1.0]
        return x_muro(z_disp) + p_scaled, z_disp - (p_scaled * ratio_z_x) * tan_t                     # [V.1.1.0]

    puntos_x, puntos_z = [x_muro(0), x_muro(H_disp)], [0.0, H_disp]                                   # [V.2.2.0] Extremos dibujados (para los ejes).
    etiquetas_valor = []                                                                              # [V.2.2.0] Valores de presión (movibles).
    obstaculos = []                                                                                   # [V.2.2.0] Textos fijos.
    etiquetas_id = []                                                                                 # [V.2.2.0] Números (n) de áreas (movibles, prioridad alta).

    # [V.2.2.0] Muro como franja gris a la izquierda de la cara y base del terreno.
    w = 0.04 * span_p                                                                                 # [V.2.2.0] Espesor visual del muro.
    ax.add_patch(patches.Polygon([(x_muro(0), 0), (x_muro(H_disp), H_disp), (x_muro(H_disp) - w, H_disp), (x_muro(0) - w, 0)],  # [V.2.2.0]
                                 facecolor=COLOR_MURO, edgecolor=BORDE_MURO, linewidth=1.2, zorder=4))  # [V.2.2.0]
    puntos_x.append(min(x_muro(0), x_muro(H_disp)) - w)                                               # [V.2.2.0]

    z_agua_eval = resultado.caso.z_agua if resultado.caso.z_agua is not None else float('inf')        # [V.1.2.1]

    def dibujar_formas_relleno(p_si_array, comp, is_water=False, draw_subdivisions=True):             # [V.1.1.0]
        """[V.1.2.1] Dibuja los polígonos de un componente, tramo a tramo (estrato / NF)."""          # [V.1.1.0]
        p_scaled_array = [p * scale_p for p in p_si_array]                                            # [V.1.1.0]
        if all(abs(p) < 1e-12 for p in p_scaled_array): return                                        # [V.1.2.1]
        color_fill, color_line = RELLENOS_COMP[comp], COLORES_COMP[comp]                              # [V.2.2.0]

        chunks, chunk_z, chunk_p = [], [], []                                                         # [V.1.1.0] Tramos continuos.
        current_id = (resultado.filas[0].estrato, resultado.filas[0].z > z_agua_eval)                 # [V.1.2.1]
        for f, p_val in zip(resultado.filas, p_scaled_array):                                         # [V.1.1.0]
            c_id = (f.estrato, f.z > z_agua_eval)                                                     # [V.1.2.1]
            z_disp = f.z * scale_z                                                                    # [V.1.1.0]
            if c_id != current_id:                                                                    # [V.1.1.0]
                chunks.append((chunk_z, chunk_p)); chunk_z, chunk_p = [z_disp], [p_val]               # [V.1.1.0]
                current_id = c_id                                                                     # [V.1.1.0]
            else:                                                                                     # [V.1.1.0]
                chunk_z.append(z_disp); chunk_p.append(p_val)                                         # [V.1.1.0]
        if chunk_z: chunks.append((chunk_z, chunk_p))                                                 # [V.1.1.0]

        last_z_bot, last_p_bot = None, None                                                           # [V.1.2.1]
        for z_arr, p_arr in chunks:                                                                   # [V.1.1.0]
            if not z_arr or all(abs(p) < 1e-12 for p in p_arr): continue                              # [V.1.2.1]
            pts = [(x_muro(z), z) for z in z_arr]                                                     # [V.1.1.0] Borde sobre el muro.
            pts += [transform(z, p) for z, p in zip(reversed(z_arr), reversed(p_arr))]                # [V.1.1.0] Borde exterior.
            ax.add_patch(patches.Polygon(pts, facecolor=color_fill, alpha=0.85, edgecolor='none', zorder=1))  # [V.1.2.1]
            out = [transform(z, p) for z, p in zip(z_arr, p_arr)]                                     # [V.1.2.1]
            ax.plot([o[0] for o in out], [o[1] for o in out], color=color_line,                       # [V.1.1.0]
                    linestyle='--' if is_water else '-', linewidth=1.5, zorder=2)                     # [V.1.1.0]
            puntos_x.extend(o[0] for o in out); puntos_z.extend(o[1] for o in out)                    # [V.2.2.0] Registra extremos.

            if draw_subdivisions:                                                                     # [V.1.1.0]
                z_top, z_bot = z_arr[0], z_arr[-1]                                                    # [V.1.1.0]
                p_top, p_bot = p_arr[0], p_arr[-1]                                                    # [V.1.1.0]
                if z_bot < H_disp - 1e-6:                                                             # [V.1.2.1] Divisoria entre tramos.
                    x2, z2 = transform(z_bot, p_bot)                                                  # [V.1.1.0]
                    ax.plot([x_muro(z_bot), x2], [z_bot, z2], color='gray', linestyle=':', linewidth=1.0, zorder=2)  # [V.1.2.1]
                xt, zt = transform(z_top, p_top)                                                      # [V.1.1.0]
                xb, zb = transform(z_bot, p_bot)                                                      # [V.1.1.0]
                repetido = (last_z_bot is not None and abs(z_top - last_z_bot) < 1e-6 and abs(p_top - last_p_bot) < umbral_p)  # [V.2.2.0]
                if abs(p_top) > umbral_p and not repetido:                                            # [V.1.2.1] Valor superior del tramo.
                    etiquetas_valor.append(ax.text(xt, zt, f" {_fmt(p_top)}" if p_top >= 0 else f"{_fmt(p_top)} ",  # [V.1.2.1]
                                                   va='bottom', ha='left' if p_top >= 0 else 'right', fontsize=8,
                                                   color=color_line, bbox=CAJA_SIMPLE, zorder=9))
                if abs(p_bot) > umbral_p and abs(p_bot - p_top) > umbral_p:                           # [V.1.2.1] Valor inferior del tramo.
                    etiquetas_valor.append(ax.text(xb, zb, f" {_fmt(p_bot)}" if p_bot >= 0 else f"{_fmt(p_bot)} ",  # [V.1.2.1]
                                                   va='top', ha='left' if p_bot >= 0 else 'right', fontsize=8,
                                                   color=color_line, bbox=CAJA_SIMPLE, zorder=9))
                last_z_bot, last_p_bot = z_bot, p_bot                                                 # [V.1.1.0]

    # [V.1.1.0] Renderiza los polígonos capa por capa según las casillas visibles.
    if vis['Suelo']: dibujar_formas_relleno([f.suelo for f in resultado.filas], 'Suelo')              # [V.1.2.1]
    if vis['Agua']: dibujar_formas_relleno([f.agua for f in resultado.filas], 'Agua', is_water=True)  # [V.1.2.1]
    if vis['Sobrecarga']: dibujar_formas_relleno([f.carga for f in resultado.filas], 'Sobrecarga', draw_subdivisions=False)  # [V.1.2.1]
    if vis['Sismo']: dibujar_formas_relleno([f.sismo for f in resultado.filas], 'Sismo')              # [V.1.2.1]

    # [V.1.2.1] Suma de fuerzas y momentos de los componentes visibles.
    sum_P, sum_M = 0.0, 0.0                                                                           # [V.1.1.0]
    for comp, clave in CLAVE_COMPONENTE.items():                                                      # [V.2.2.0]
        if vis.get(comp):                                                                             # [V.2.2.0]
            P_c, M_c = resultado.componentes.get(clave, (0.0, 0.0, 0.0))[:2]                          # [V.2.2.0]
            sum_P += P_c; sum_M += M_c                                                                # [V.1.1.0]
    # [V.2.2.0] "E_TOTAL" si están visibles todos los componentes que existen (antes contaba los que valen 0).
    falta_alguno = any(abs(resultado.componentes.get(cl, (0.0,))[0]) > 1e-9 and not vis.get(cp) for cp, cl in CLAVE_COMPONENTE.items())  # [V.2.2.0]
    lbl_title = "E_PARCIAL" if falta_alguno else "E_TOTAL"                                            # [V.1.2.1]

    max_F = max([abs(d.fuerza) for d in resultado.detalles] + [abs(sum_P), 1e-12]) * abs(scale_F)    # [V.2.2.0] Para umbral relativo de vectores.
    x_borde_dibujo = max(puntos_x)                                                                    # [V.2.2.0] Borde derecho real del dibujo.

    if vis.get('Vectores', True):                                                                     # [V.1.1.0]
        # [V.1.2.1] Vectores parciales numerados (uno por área del cálculo).
        for d in resultado.detalles:                                                                  # [V.1.1.0]
            if not vis.get(d.componente, True): continue                                              # [V.1.1.0]
            if abs(d.fuerza * scale_F) < 0.01 * max_F: continue                                       # [V.1.2.1] Umbral relativo.
            z_c = d.z_centro * scale_z                                                                # [V.1.1.0]
            color_arrow = COLORES_COMP.get(d.componente, 'gray')                                      # [V.1.1.0]
            xc, zc_shape = transform(z_c, d.p_centro * scale_p)                                       # [V.1.1.0]
            ax.annotate('', xy=(x_muro(z_c), z_c), xytext=(xc, zc_shape),                             # [V.1.1.0]
                        arrowprops=dict(arrowstyle='-|>', color=color_arrow, lw=1.3, mutation_scale=10, alpha=0.9), zorder=5)  # [V.1.2.1]
            etiquetas_id.append(ax.text(xc, zc_shape, f"({d.id})", ha='center', va='center', fontsize=8,  # [V.1.2.1]
                                        color=color_arrow, fontweight='bold', bbox=CAJA_SIMPLE, zorder=9))  # [V.1.2.1] Encima de la flecha roja.

        # [V.1.2.1] GRAN FLECHA ROJA del empuje resultante, aplicada a y_T desde la base.
        if abs(sum_P * scale_F) > 1e-3 * max_F and abs(sum_P) > 1e-12:                                # [V.1.2.1]
            Y_T = (sum_M / sum_P) * scale_z                                                           # [V.1.1.0] Brazo desde la base.
            z_T = H_disp - Y_T                                                                        # [V.1.1.0] Profundidad de aplicación.
            x_wall = x_muro(z_T)                                                                      # [V.1.1.0]
            x_cola = x_borde_dibujo + 0.30 * span_p                                                   # [V.1.2.1] La cola siempre fuera del diagrama.
            ax.add_patch(FancyArrowPatch((x_cola, z_T), (x_wall, z_T), arrowstyle='simple,head_length=1.1,head_width=1.3,tail_width=0.45',  # [V.2.2.0]
                                         mutation_scale=16, facecolor=COLOR_RESULTANTE, edgecolor='#7a0000', linewidth=0.8, alpha=0.95, zorder=8))  # [V.2.2.0]
            ax.plot([x_cola, x_cola], [z_T, H_disp], color=COLOR_RESULTANTE, lw=0.8, ls='--', zorder=3)  # [V.2.2.0] Guía del brazo y_T.
            ax.plot([x_cola - 0.02 * span_p, x_cola + 0.02 * span_p], [H_disp, H_disp], color=COLOR_RESULTANTE, lw=0.8)  # [V.2.2.0]
            t_res = ax.annotate(f"{lbl_title} = {_fmt(sum_P * scale_F)} {unidad_F}\ny_T = {_fmt(Y_T)} {unidad_z}",  # [V.1.2.1]
                                xy=(x_cola, z_T), xytext=(6, 0), textcoords='offset points', va='center', ha='left',
                                color=COLOR_RESULTANTE, fontweight='bold', fontsize=9,
                                bbox=dict(boxstyle='round,pad=0.35', facecolor='white', edgecolor=COLOR_RESULTANTE, linewidth=1.0), zorder=9)
            obstaculos.append(t_res)                                                                  # [V.2.2.0]
            puntos_x.append(x_cola)                                                                   # [V.2.2.0]

    # [V.1.2.1] Ejes dinámicos: se ajustan a lo que realmente se dibujó (+ márgenes relativos).
    x_lo, x_hi = min(puntos_x), max(puntos_x)                                                         # [V.2.2.0]
    pad_x = 0.06 * (x_hi - x_lo if x_hi > x_lo else span_p)                                           # [V.2.2.0]
    z_lo = min(puntos_z + [0.0])                                                                      # [V.2.2.0] Incluye diagramas inclinados por α.
    pad_z = 0.05 * H_disp if H_disp > 0 else 0.5                                                      # [V.2.2.0]
    _fijar_limites(ax, x_lo - pad_x, x_hi + pad_x, z_lo - pad_z, H_disp + pad_z)                      # [V.2.2.0]
    ax.axhline(H_disp, color='#4a3626', lw=1.2, zorder=3)                                             # [V.2.2.0] Base del muro.

    # [V.1.1.0] Leyenda de colores y tipos de línea.
    leyenda = []                                                                                      # [V.1.1.0]
    nombres = {'Suelo': 'Suelo', 'Agua': 'Agua', 'Sobrecarga': 'Sobrecargas', 'Sismo': 'Sismo'}      # [V.2.2.0]
    for comp in ['Suelo', 'Agua', 'Sobrecarga', 'Sismo']:                                             # [V.1.2.1]
        if vis.get(comp):                                                                             # [V.1.2.1]
            leyenda.append(mlines.Line2D([0], [0], color=COLORES_COMP[comp], lw=1.5, linestyle='--' if comp == 'Agua' else '-', label=nombres[comp]))  # [V.1.2.1]
    if vis.get('Vectores', True) and abs(sum_P) > 1e-12:                                              # [V.2.2.0]
        leyenda.append(mlines.Line2D([0], [0], color=COLOR_RESULTANTE, lw=3, label='Resultante'))     # [V.2.2.0]
    ax.set_xlabel(f"Presión horizontal ({unidad_p})", fontsize=9)                                     # [V.1.1.0]
    ax.set_ylabel(f"Profundidad z ({unidad_z})", fontsize=9)                                          # [V.1.1.0]
    ax.set_xticks([])                                                                                 # [V.1.1.0] Valores ya rotulados sobre el diagrama.
    ax.tick_params(axis='y', labelsize=8)                                                             # [V.2.2.0]
    ax.set_title(titulo_custom, fontweight='bold', fontsize=10)                                       # [V.1.1.0]

    # [V.2.2.0] Ajuste final: los textos nunca quedan cortados ni se pisan entre sí.
    rend = _renderer(ax)                                                                              # [V.2.2.0]
    _expandir_limites_a_textos(ax, rend)                                                              # [V.2.2.0]
    leg = _colocar_leyenda(ax, rend, leyenda, obstaculos, etiquetas_valor + etiquetas_id)            # [V.1.2.1] Esquina que no tape la resultante.
    etiquetas_valor.sort(key=lambda t: t.get_position()[1])                                           # [V.2.2.0] De arriba hacia abajo.
    etiquetas_id.sort(key=lambda t: t.get_position()[1])                                              # [V.2.2.0]
    for _ in range(2):                                                                                # [V.2.2.0] 2 pasadas: al ajustar ejes cambian los píxeles.
        _evitar_solapes(ax, rend, etiquetas_id + etiquetas_valor, obstaculos=obstaculos + ([leg] if leg else []))  # [V.2.2.0] Primero (n), luego valores.
        _expandir_limites_a_textos(ax, rend)                                                          # [V.2.2.0]
