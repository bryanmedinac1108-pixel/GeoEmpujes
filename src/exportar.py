"""
Módulo de Exportación de Resultados.
Genera el registro CSV continuo y una Memoria de Cálculo en PDF,
con la vista general y el desglose de todas las capas aisladas en la Sección 7.
"""
# Importa la librería estándar para crear y escribir archivos de Excel (valores separados por comas)
import csv
# Importa 'os' para interactuar con el sistema operativo (verificar si los archivos de imagen existen antes de insertarlos)
import os
# Importa la librería matemática para conversiones de ángulos a grados en la memoria de cálculo
import math
# Importa la función del sismo para poder imprimir su valor exacto en el reporte
from calculo import calcular_K_dinamico

# Función principal que recibe todos los datos procesados y las escalas de conversión de unidades de la interfaz
def exportar(resultado, ruta_csv, rutas_png, scale_z=1.0, scale_p=1.0, scale_gamma=1.0, lbl_z="m", lbl_p="kPa", lbl_gamma="kN/m³"):
    # Lista para rastrear todos los archivos físicos que se crean en la computadora del usuario
    archivos_generados = []
    
    # Flexibilidad del código: Si la interfaz manda una sola ruta de imagen (string), la convierte en un diccionario
    if isinstance(rutas_png, str):
        rutas_png = {'principal': rutas_png}
    
    # =========================================================================
    # 1. GENERACIÓN DEL ARCHIVO TABULAR (CSV)
    # =========================================================================
    # Abre (o crea) el archivo CSV en modo escritura ('w') asegurando la codificación UTF-8 para acentos
    with open(ruta_csv, mode='w', newline='', encoding='utf-8') as f:
        # Configura el escritor CSV usando punto y coma (;) como separador para compatibilidad con Excel en español
        writer = csv.writer(f, delimiter=';')
        # Escribe la primera fila con los encabezados dinámicos (incluyendo las etiquetas de unidades elegidas)
        writer.writerow([f'z ({lbl_z})', 'Estrato', f'Sigma_v ({lbl_p})', 'K', 
                         f'Suelo ({lbl_p})', f'Agua ({lbl_p})', f'Sobrecarga ({lbl_p})', 
                         f'Sismo ({lbl_p})', f'Total ({lbl_p})'])
        # Recorre cada milímetro calculado en el motor matemático
        for fila in resultado.filas:
            # Escribe una nueva fila multiplicando cada valor interno (SI) por el factor de escala de la interfaz
            writer.writerow([
                f"{fila.z * scale_z:.4f}", fila.estrato, f"{fila.sigma_v * scale_p:.4f}",
                f"{fila.k:.4f}", f"{fila.suelo * scale_p:.4f}", f"{fila.agua * scale_p:.4f}",
                f"{fila.carga * scale_p:.4f}", f"{fila.sismo * scale_p:.4f}", f"{fila.total * scale_p:.4f}"
            ])
    # Añade el archivo CSV a la lista de éxitos
    archivos_generados.append(ruta_csv)
    
    # =========================================================================
    # 2. GENERACIÓN DE LA MEMORIA DE CÁLCULO EN PDF
    # =========================================================================
    # Usa un bloque try-except por si la computadora del usuario no tiene instalada la librería ReportLab
    try:
        # Importa los tamaños de hoja estándar (A4)
        from reportlab.lib.pagesizes import A4
        # Importa los elementos básicos de construcción de un documento (Plantilla, Párrafos, Espacios, Imágenes, Tablas, Saltos de página)
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
        # Importa el gestor de estilos tipográficos y de color
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        # Importa las constantes de alineación de texto (Justificado, Centrado)
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
        
        # Define que el archivo PDF se guardará en la misma ruta que el CSV, pero cambiando la extensión
        ruta_pdf = ruta_csv.replace('.csv', '.pdf')
        # Inicializa la plantilla del documento en tamaño A4 con márgenes de 40 puntos en todos los bordes
        doc = SimpleDocTemplate(ruta_pdf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        # Carga la hoja de estilos por defecto de ReportLab
        styles = getSampleStyleSheet()
        
        # --- DEFINICIÓN DE ESTILOS TIPOGRÁFICOS PERSONALIZADOS ---
        # Título principal: Letra grande, azul oscuro
        st_title = ParagraphStyle('TitleCustom', parent=styles['Title'], fontSize=16, spaceAfter=6, textColor=colors.HexColor("#1b365d"))
        # Subtítulo: Centrado, gris oscuro, con margen inferior
        st_subtitle = ParagraphStyle('SubtitleCustom', parent=styles['Normal'], fontSize=12, spaceAfter=20, alignment=TA_CENTER, textColor=colors.HexColor("#555555"))
        # Encabezado 1 (Secciones): Tamaño 13, color azul claro
        st_h1 = ParagraphStyle('H1Custom', parent=styles['Heading1'], fontSize=13, spaceAfter=10, textColor=colors.HexColor("#2b5797"))
        # Encabezado 2 (Subsecciones): Tamaño 11, casi negro
        st_h2 = ParagraphStyle('H2Custom', parent=styles['Heading2'], fontSize=11, spaceAfter=8, textColor=colors.HexColor("#333333"))
        # Cuerpo de texto normal: Tamaño 10, texto justificado
        st_body = ParagraphStyle('BodyCustom', parent=styles['Normal'], fontSize=10, spaceAfter=8, alignment=TA_JUSTIFY, leading=14)
        # Estilo para fórmulas: Centrado, negro puro, sin mucho espacio
        st_formula = ParagraphStyle('FormulaCustom', parent=styles['Normal'], fontSize=10, spaceAfter=4, alignment=TA_CENTER, leading=14, textColor=colors.HexColor("#000000"))
        # Estilo indentado para listados (con sangría izquierda de 20 puntos)
        st_indent = ParagraphStyle('Indented', parent=st_body, leftIndent=20, spaceAfter=4)
        
        # "Story" es la lista secuencial donde se irán apilando todos los elementos del PDF de arriba hacia abajo
        story = []
        c = resultado.caso # Atajo para acceder a los datos de entrada
        
        # Construye dinámicamente las etiquetas combinadas para Fuerza (p·z) y Momento (p·z²)
        lbl_F = f"{lbl_p}·{lbl_z}"
        lbl_M = f"{lbl_p}·{lbl_z}²"
        # Escala combinada para llevar las Fuerzas del Sistema Internacional a la unidad del usuario
        scale_F = scale_p * scale_z
        
        # Escribe los títulos en la "Historia" del documento
        story.append(Paragraph("MEMORIA DE CÁLCULO GEOTÉCNICO", st_title))
        story.append(Paragraph("Análisis de Empujes Laterales", st_subtitle))
        story.append(Spacer(1, 15)) # Añade un espacio en blanco de 15 puntos
        
        # =========================================================
        # SECCIÓN 1: DATOS DE PARTIDA
        # =========================================================
        story.append(Paragraph("1. DATOS DE PARTIDA", st_h1))
        story.append(Paragraph("1.1 Parámetros Generales y Geometría", st_h2))
        
        # Prepara el texto del nivel freático. Si es nulo, avisa que no hay.
        nf_txt = f"{c.z_agua * scale_z:.2f} {lbl_z}" if c.z_agua is not None else "No existe N.F."
        # Escala el peso del agua a las unidades seleccionadas
        peso_agua = c.gamma_agua * scale_gamma
        
        # Matriz de datos (Lista de listas) para construir la tabla de geometría
        datos_gen = [
            ["Altura total del muro (H):", f"{c.altura * scale_z:.2f} {lbl_z}", "Inclinación del muro (β):", f"{c.beta}°"],
            ["Condición física:", c.condicion.capitalize(), "Inclinación del relleno (α):", f"{c.alpha}°"],
            ["Nivel Freático (NF):", nf_txt, "Peso específico del agua:", f"{peso_agua:.2f} {lbl_gamma}"],
            ["Coef. Sísmico Horiz. (kh):", f"{c.kh}", "Coef. Sísmico Vert. (kv):", f"{c.kv}"]
        ]
        # Crea la tabla definiendo anchos fijos para las 4 columnas
        t_gen = Table(datos_gen, colWidths=[140, 100, 140, 100])
        # Aplica estilos masivos a la tabla (Fondo gris claro, rejilla gris, fuente Helvetica)
        t_gen.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey)
        ]))
        story.append(t_gen)
        story.append(Spacer(1, 10))
        
        # Tabla de Estratos
        story.append(Paragraph("1.2 Perfil Estratigráfico", st_h2))
        # Fila de encabezado de la matriz de estratos
        datos_estratos = [["Estrato", f"Espesor h ({lbl_z})", f"γ natural\n({lbl_gamma})", f"γ sat.\n({lbl_gamma})", "φ' (°)", f"Cohesión c'\n({lbl_p})", "Fricción muro\nδ (°)"]]
        # Recorre la lista de estratos para inyectarlos en la matriz de la tabla
        for i, est in enumerate(c.estratos):
            datos_estratos.append([
                f"Estrato {i+1}", f"{est.h * scale_z:.2f}", f"{est.gamma * scale_gamma:.2f}", 
                f"{est.gamma_sat * scale_gamma:.2f}", f"{est.phi:.1f}", f"{est.cohesion * scale_p:.2f}", f"{est.delta:.1f}"
            ])
        t_est = Table(datos_estratos, colWidths=[60, 75, 75, 75, 50, 75, 75])
        # Pinta la primera fila (0,0) a (-1,0) de azul oscuro con letras blancas, y bordes grises
        t_est.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2b5797")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t_est)
        story.append(Spacer(1, 15))

        # =========================================================
        # SECCIÓN 2: CÁLCULO DE COEFICIENTES (K)
        # =========================================================
        story.append(Paragraph("2. CÁLCULO DE COEFICIENTES (K)", st_h1))
        story.append(Paragraph(f"El análisis estático se realiza mediante <b>{c.metodo.upper()}</b> en condición <b>{c.condicion.upper()}</b>.", st_body))
        
        # Lógica para detectar si hay configuración sísmica
        hay_sismo = abs(c.kh) > 1e-12 or abs(c.kv) > 1e-12
        if hay_sismo:
            # Calcula el ángulo inercial theta para imprimirlo documentado en el reporte
            theta_s = math.degrees(math.atan2(c.kh, 1.0-c.kv))
            story.append(Paragraph(
                f"Para la condición sísmica se emplea <b>Mononobe-Okabe</b>, con θ = atan[kh/(1-kv)] = <b>{theta_s:.4f}°</b>. "
                "La formulación se aplica al suelo granular (c'=0) y el agua se considera por separado.", st_body))

        # Bucle para detallar qué fórmula exacta de K se usó para cada estrato
        for i, est in enumerate(c.estratos):
            # Busca en los resultados la K utilizada específicamente para el techo de este estrato
            k_val = next((f.k for f in resultado.filas if f.estrato == i+1), 0.0)
            story.append(Paragraph(f"<b>Estrato {i+1}</b> (φ' = {est.phi}°, δ = {est.delta}°):", st_body))
            
            # Condicionales que imprimen cadenas de texto con la fórmula matemática explícita y su resultado final
            if c.condicion == 'reposo':
                story.append(Paragraph(f"<b>Jaky:</b> K0 = 1 - sen({est.phi}°) = <b>{k_val:.5f}</b>", st_formula))
            elif c.metodo == 'Coulomb' and c.condicion == 'activa':
                story.append(Paragraph(f"<b>Coulomb activo:</b> Ka = sen²({c.beta}°+{est.phi}°) / [sen²({c.beta}°)·sen({c.beta}°-{est.delta}°)·(1 + √[(sen({est.phi}°+{est.delta}°)·sen({est.phi}°-{c.alpha}°))/(sen({c.beta}°-{est.delta}°)·sen({c.beta}°+{c.alpha}°))])²] = <b>{k_val:.5f}</b>", st_formula))
            elif c.metodo == 'Coulomb' and c.condicion == 'pasiva':
                story.append(Paragraph(f"<b>Coulomb pasivo:</b> Kp = sen²({c.beta}°-{est.phi}°) / [sen²({c.beta}°)·sen({c.beta}°+{est.delta}°)·(1 - √[(sen({est.phi}°+{est.delta}°)·sen({est.phi}°+{c.alpha}°))/(sen({c.beta}°+{est.delta}°)·sen({c.beta}°+{c.alpha}°))])²] = <b>{k_val:.5f}</b>", st_formula))
            elif c.metodo == 'Rankine':
                # Adapta los signos de la fórmula de Rankine si es activa (-) o pasiva (+)
                signo = '-' if c.condicion == 'activa' else '+'
                signo_den = '+' if c.condicion == 'activa' else '-'
                story.append(Paragraph(f"<b>Rankine {c.condicion}:</b> K = cos({c.alpha}°)·[cos({c.alpha}°) {signo} √(cos²({c.alpha}°)-cos²({est.phi}°))]/[cos({c.alpha}°) {signo_den} √(cos²({c.alpha}°)-cos²({est.phi}°))] = <b>{k_val:.5f}</b>", st_formula))

            # Si el sismo está activo, recalcula e imprime los coeficientes de Mononobe-Okabe
            if hay_sismo and c.condicion in ('activa','pasiva'):
                ke = calcular_K_dinamico(est.phi, c.alpha, c.beta, est.delta, c.kh, c.kv)
                ke_eq = (1.0-c.kv)*ke
                nombre_ke = 'KAE' if c.condicion == 'activa' else 'KPE'
                story.append(Paragraph(f"<b>Mononobe-Okabe:</b> {nombre_ke} = <b>{ke:.5f}</b>; coeficiente equivalente (1-kv){nombre_ke} = <b>{ke_eq:.5f}</b>", st_formula))
            story.append(Spacer(1, 10))

        # Si el usuario agregó sobrecargas, añade un bloque teórico que explica qué fórmulas se usarán
        if c.cargas:
            story.append(Paragraph("2.1 Formulación de sobrecargas", st_h2))
            story.append(Paragraph(
                "<b>Uniforme:</b> Δσh = K·q.<br/>"
                "<b>Franja finita:</b> Integrada según Jarquio (1981) y perfil continuo de Boussinesq modificado.<br/>"
                "<b>Lineal / Puntual:</b> Formulación de elasticidad para muro vertical y relleno horizontal.", st_body))

        # =========================================================
        # SECCIÓN 3: ESFUERZOS LATERALES (PASO A PASO)
        # =========================================================
        story.append(Paragraph("3. CÁLCULO DE ESFUERZOS LATERALES", st_h1))
        story.append(Paragraph("Se evalúan las profundidades críticas usando esfuerzo vertical efectivo. La presión del agua se suma por separado como u = γw·hw.", st_body))
        
        # Lógica "cazadora de puntos críticos": Busca en la matriz de filas únicamente los puntos donde hay cambios bruscos
        criticos = []
        for i, f in enumerate(resultado.filas):
            if i == 0:
                criticos.append((f, "Cima del muro")) # Caza Z=0
                continue
            prev = resultado.filas[i-1]
            if prev.estrato != f.estrato: # Caza el cruce entre dos estratos
                criticos.append((prev, f"Base del Estrato {prev.estrato}"))
                criticos.append((f, f"Cima del Estrato {f.estrato} (Aplica nuevo K)"))
            elif prev.agua == 0 and f.agua > 0: # Caza exactamente el inicio del Nivel Freático
                criticos.append((f, "Aparición de Nivel Freático"))
            elif i == len(resultado.filas)-1: # Caza el fondo del muro
                criticos.append((f, f"Base del Muro (Estrato {f.estrato})"))
                
        # Imprime la justificación matemática para cada uno de los puntos críticos cazados
        for f, desc in criticos:
            z_s, sv_s, sh_s = f.z * scale_z, f.sigma_v * scale_p, f.suelo * scale_p
            story.append(Paragraph(f"<b>• z = {z_s:.2f} {lbl_z} ({desc}):</b>", st_body))
            
            # Reemplazo de valores en la ecuación: Esfuerzo Efectivo Vertical
            detalles_txt = f"<font color='#444444'>Esfuerzo vertical efectivo:</font> σ'_v = {sv_s:.2f} {lbl_p}<br/>"
            
            est = c.estratos[f.estrato-1]
            c_val = est.cohesion * scale_p
            # Evalúa si imprimir la fórmula con la resta de cohesión (activa) o suma (pasiva)
            if c_val > 0 and c.condicion == 'activa':
                detalles_txt += f"<font color='#444444'>Presión lateral activa:</font> σh = {sv_s:.2f}×{f.k:.3f} - 2({c_val:.2f})√{f.k:.3f} = <b>{sh_s:.2f} {lbl_p}</b><br/>"
            elif c_val > 0 and c.condicion == 'pasiva':
                detalles_txt += f"<font color='#444444'>Presión lateral pasiva:</font> σh = {sv_s:.2f}×{f.k:.3f} + 2({c_val:.2f})√{f.k:.3f} = <b>{sh_s:.2f} {lbl_p}</b><br/>"
            else: # Suelo granular puro sin cohesión
                detalles_txt += f"<font color='#444444'>Presión lateral del suelo:</font> σh = {sv_s:.2f}×{f.k:.3f} = <b>{sh_s:.2f} {lbl_p}</b><br/>"

            # Si el punto tiene agua, sobrecargas o sismo, imprime esa presión particular también
            if f.agua > 0:
                detalles_txt += f"<font color='#444444'>Presión de poros:</font> u = <b>{f.agua * scale_p:.2f} {lbl_p}</b><br/>"
            if abs(f.carga) > 1e-10:
                detalles_txt += f"<font color='#444444'>Sobrecargas:</font> Δσh,q = <b>{f.carga * scale_p:.2f} {lbl_p}</b><br/>"
            if abs(f.sismo) > 1e-10:
                detalles_txt += f"<font color='#444444'>Incremento sísmico:</font> Δσh,E = <b>{f.sismo * scale_p:.2f} {lbl_p}</b><br/>"
            
            # Inserta el bloque de texto con sangría (indentado)
            story.append(Paragraph(detalles_txt, st_indent))
            story.append(Spacer(1, 4))
            
        story.append(Spacer(1, 10))

        # =========================================================
        # SECCIÓN 4: CÁLCULO DEL EMPUJE TOTAL (ÁREAS)
        # =========================================================
        story.append(Paragraph("4. CÁLCULO DEL EMPUJE TOTAL (Áreas Geométricas)", st_h1))
        story.append(Paragraph("El empuje total se obtiene integrando el diagrama de presiones. Los tramos lineales se descomponen en rectángulos y triángulos; los diagramas no lineales de sobrecargas localizadas se integran numéricamente mediante trapecios.", st_body))
        
        # Recorre todas las formas geométricas (Áreas) detectadas por el motor en calculo.py
        for d in resultado.detalles:
            # Filtro para ignorar micro-fuerzas de ruido numérico
            if abs(d.fuerza * scale_F) > 0.005:
                f_val, h_s, p1_s = d.fuerza * scale_F, d.h_tramo * scale_z, d.p_calc * scale_p
                
                # Prepara el string textual de la fórmula (Base x Altura o Base x Altura / 2)
                if d.forma == 'Triángulo':
                    f_str = f"({p1_s:.2f} × {h_s:.2f}) / 2"
                elif d.forma == 'Rectángulo':
                    f_str = f"{p1_s:.2f} × {h_s:.2f}"
                else: # Aplica para integrales curvas (Sismo o Elasticidad) o analíticas puras (Jarquio)
                    f_str = f"Fórmula analítica ({d.forma})"
                # Pone la etiqueta E1, E2, E3, etc.
                circle_num = f"E{d.id}"

                # Imprime la justificación del área: "Área E1 (Suelo - Triángulo): (Base x Alt) = Fuerza"
                story.append(Paragraph(f"<b>• Área {circle_num} ({d.componente} - {d.forma}):</b> {f_str} = <b>{f_val:.2f} {lbl_F}</b>", st_indent))
                
        story.append(Spacer(1, 15))

        # =========================================================
        # SECCIÓN 5: TOTALES
        # =========================================================
        story.append(Paragraph("5. RESUMEN DE COMPONENTES", st_h1))
        # Encabezado de la tabla de resumen final
        datos_res = [["Fuerza Agrupada", f"Fuerza P ({lbl_F})", f"Momento M ({lbl_M})", f"Brazo y ({lbl_z})"]]
        # Recorre las sumatorias globales (Suelo, Agua, Sobrecargas, Sismo)
        for comp, vals in resultado.componentes.items():
            if abs(vals[0] * scale_F) > 0.005:
                datos_res.append([comp, f"{vals[0]*scale_F:.3f}", f"{vals[1]*scale_F*scale_z:.3f}", f"{vals[2]*scale_z:.3f}"])
        # Añade la fila del GRAN TOTAL
        datos_res.append(["SUMATORIA TOTAL", f"{resultado.total*scale_F:.3f}", f"{resultado.momento*scale_F*scale_z:.3f}", f"{resultado.y*scale_z:.3f}"])
        
        # Dibuja la tabla con encabezado azul oscuro y la fila de Sumatoria Total en gris claro
        t_res = Table(datos_res, colWidths=[140, 110, 120, 110])
        t_res.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1b365d")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e0e0e0")), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t_res)
        
        story.append(PageBreak()) # Exige un salto forzoso a una nueva hoja para los anexos gráficos

        # =========================================================
        # SECCIÓN 6: GRÁFICO (Nueva página)
        # =========================================================
        story.append(Paragraph("6. DIAGRAMA DE ESFUERZOS HORIZONTALES", st_h1))
        # Extrae la ruta de la gráfica general ("principal") generada previamente por matplotlib
        ruta_main = rutas_png.get('principal')
        if ruta_main and os.path.exists(ruta_main):
            # Carga la imagen al PDF con dimensiones ajustadas
            story.append(RLImage(ruta_main, width=460, height=360))
            # La registra para notificar al usuario sobre su creación exitosa
            archivos_generados.append(ruta_main)
            
        # Extrae todas las rutas de los gráficos auxiliares aislados (excluyendo 'principal')
        aislados = [k for k in rutas_png.keys() if k != 'principal']
        # Si el motor gráfico generó capas aisladas (Suelo.png, Agua.png, Sismo.png...)
        if aislados:
            story.append(PageBreak()) # Salto a nueva hoja
            story.append(Paragraph("7. DESGLOSE GRÁFICO POR COMPONENTES", st_h1))
            story.append(Paragraph("A continuación se presentan los diagramas de presiones y líneas de acción aisladas para cada solicitación existente en el análisis:", st_body))
            
            # Recorre e inserta apiladamente cada una de las gráficas aisladas
            for clave in aislados:
                ruta_iso = rutas_png[clave]
                if os.path.exists(ruta_iso):
                    story.append(Spacer(1, 10))
                    story.append(RLImage(ruta_iso, width=400, height=310))
                    archivos_generados.append(ruta_iso)
            
        # ENSAMBLAJE FINAL: Toma la lista `story` y la inyecta al archivo de disco duro PDF
        doc.build(story)
        archivos_generados.append(ruta_pdf)
        
    except ImportError:
        # En caso de que falle la importación de ReportLab
        archivos_generados.append("\n(Aviso: Instala reportlab para generar el PDF)")
        
    # Retorna las rutas de todos los archivos .csv, .pdf y .png generados al programa interfaz para mostrarlos en el popup
    return archivos_generados