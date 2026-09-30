"""
Módulo de Exportación de Resultados.
Genera el registro CSV continuo y una Memoria de Cálculo en PDF,
con la vista general y el desglose de todas las capas aisladas en la Sección 7.
"""
import csv
import os
import math
from calculo import calcular_K_dinamico

def exportar(resultado, ruta_csv, rutas_png, scale_z=1.0, scale_p=1.0, scale_gamma=1.0, lbl_z="m", lbl_p="kPa", lbl_gamma="kN/m³"):
    archivos_generados = []
    
    # Soporta tanto string directo como diccionario de imágenes
    if isinstance(rutas_png, str):
        rutas_png = {'principal': rutas_png}
    
    # 1. GENERACIÓN DEL CSV 
    with open(ruta_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([f'z ({lbl_z})', 'Estrato', f'Sigma_v ({lbl_p})', 'K', 
                         f'Suelo ({lbl_p})', f'Agua ({lbl_p})', f'Sobrecarga ({lbl_p})', 
                         f'Sismo ({lbl_p})', f'Total ({lbl_p})'])
        for fila in resultado.filas:
            writer.writerow([
                f"{fila.z * scale_z:.4f}", fila.estrato, f"{fila.sigma_v * scale_p:.4f}",
                f"{fila.k:.4f}", f"{fila.suelo * scale_p:.4f}", f"{fila.agua * scale_p:.4f}",
                f"{fila.carga * scale_p:.4f}", f"{fila.sismo * scale_p:.4f}", f"{fila.total * scale_p:.4f}"
            ])
    archivos_generados.append(ruta_csv)
    
    # 2. GENERACIÓN DE LA MEMORIA DE CÁLCULO EN PDF
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
        
        ruta_pdf = ruta_csv.replace('.csv', '.pdf')
        doc = SimpleDocTemplate(ruta_pdf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        st_title = ParagraphStyle('TitleCustom', parent=styles['Title'], fontSize=16, spaceAfter=6, textColor=colors.HexColor("#1b365d"))
        st_subtitle = ParagraphStyle('SubtitleCustom', parent=styles['Normal'], fontSize=12, spaceAfter=20, alignment=TA_CENTER, textColor=colors.HexColor("#555555"))
        st_h1 = ParagraphStyle('H1Custom', parent=styles['Heading1'], fontSize=13, spaceAfter=10, textColor=colors.HexColor("#2b5797"))
        st_h2 = ParagraphStyle('H2Custom', parent=styles['Heading2'], fontSize=11, spaceAfter=8, textColor=colors.HexColor("#333333"))
        st_body = ParagraphStyle('BodyCustom', parent=styles['Normal'], fontSize=10, spaceAfter=8, alignment=TA_JUSTIFY, leading=14)
        st_formula = ParagraphStyle('FormulaCustom', parent=styles['Normal'], fontSize=10, spaceAfter=4, alignment=TA_CENTER, leading=14, textColor=colors.HexColor("#000000"))
        st_indent = ParagraphStyle('Indented', parent=st_body, leftIndent=20, spaceAfter=4)
        
        story = []
        c = resultado.caso
        lbl_F = f"{lbl_p}·{lbl_z}"
        lbl_M = f"{lbl_p}·{lbl_z}²"
        scale_F = scale_p * scale_z
        
        # PORTADA Y TÍTULO
        story.append(Paragraph("MEMORIA DE CÁLCULO GEOTÉCNICO", st_title))
        story.append(Paragraph("Análisis de Empujes Laterales (Paso a Paso)", st_subtitle))
        story.append(Spacer(1, 15))
        
        # =========================================================
        # SECCIÓN 1: DATOS DE PARTIDA
        # =========================================================
        story.append(Paragraph("1. DATOS DE PARTIDA", st_h1))
        story.append(Paragraph("1.1 Parámetros Generales y Geometría", st_h2))
        
        nf_txt = f"{c.z_agua * scale_z:.2f} {lbl_z}" if c.z_agua is not None else "No existe N.F."
        peso_agua = c.gamma_agua * scale_gamma
        
        datos_gen = [
            ["Altura total del muro (H):", f"{c.altura * scale_z:.2f} {lbl_z}", "Inclinación del muro (β):", f"{c.beta}°"],
            ["Condición física:", c.condicion.capitalize(), "Inclinación del relleno (α):", f"{c.alpha}°"],
            ["Nivel Freático (NF):", nf_txt, "Peso específico del agua:", f"{peso_agua:.2f} {lbl_gamma}"],
            ["Coef. Sísmico Horiz. (kh):", f"{c.kh}", "Coef. Sísmico Vert. (kv):", f"{c.kv}"]
        ]
        t_gen = Table(datos_gen, colWidths=[140, 100, 140, 100])
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
        
        story.append(Paragraph("1.2 Perfil Estratigráfico", st_h2))
        datos_estratos = [["Estrato", f"Espesor h ({lbl_z})", f"γ natural\n({lbl_gamma})", f"γ sat.\n({lbl_gamma})", "φ' (°)", f"Cohesión c'\n({lbl_p})", "Fricción muro\nδ (°)"]]
        for i, est in enumerate(c.estratos):
            datos_estratos.append([
                f"Estrato {i+1}", f"{est.h * scale_z:.2f}", f"{est.gamma * scale_gamma:.2f}", 
                f"{est.gamma_sat * scale_gamma:.2f}", f"{est.phi:.1f}", f"{est.cohesion * scale_p:.2f}", f"{est.delta:.1f}"
            ])
        t_est = Table(datos_estratos, colWidths=[60, 75, 75, 75, 50, 75, 75])
        t_est.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2b5797")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t_est)
        story.append(Spacer(1, 15))

        # =========================================================
        # SECCIÓN 2: CÁLCULO DE COEFICIENTES (K)
        # =========================================================
        story.append(Paragraph("2. CÁLCULO DE COEFICIENTES (K)", st_h1))
        story.append(Paragraph(f"El análisis estático se realiza mediante <b>{c.metodo.upper()}</b> en condición <b>{c.condicion.upper()}</b>.", st_body))
        hay_sismo = abs(c.kh) > 1e-12 or abs(c.kv) > 1e-12
        if hay_sismo:
            theta_s = math.degrees(math.atan2(c.kh, 1.0-c.kv))
            story.append(Paragraph(
                f"Para la condición sísmica se emplea <b>Mononobe-Okabe</b>, con θ = atan[kh/(1-kv)] = <b>{theta_s:.4f}°</b>. "
                "La formulación se aplica al suelo granular (c'=0) y el agua se considera por separado.", st_body))

        for i, est in enumerate(c.estratos):
            k_val = next((f.k for f in resultado.filas if f.estrato == i+1), 0.0)
            story.append(Paragraph(f"<b>Estrato {i+1}</b> (φ' = {est.phi}°, δ = {est.delta}°):", st_body))
            if c.condicion == 'reposo':
                story.append(Paragraph(f"<b>Jaky:</b> K0 = 1 - sen({est.phi}°) = <b>{k_val:.5f}</b>", st_formula))
            elif c.metodo == 'Coulomb' and c.condicion == 'activa':
                story.append(Paragraph(f"<b>Coulomb activo:</b> Ka = sen²({c.beta}°+{est.phi}°) / [sen²({c.beta}°)·sen({c.beta}°-{est.delta}°)·(1 + √[(sen({est.phi}°+{est.delta}°)·sen({est.phi}°-{c.alpha}°))/(sen({c.beta}°-{est.delta}°)·sen({c.beta}°+{c.alpha}°))])²] = <b>{k_val:.5f}</b>", st_formula))
            elif c.metodo == 'Coulomb' and c.condicion == 'pasiva':
                story.append(Paragraph(f"<b>Coulomb pasivo:</b> Kp = sen²({c.beta}°-{est.phi}°) / [sen²({c.beta}°)·sen({c.beta}°+{est.delta}°)·(1 - √[(sen({est.phi}°+{est.delta}°)·sen({est.phi}°+{c.alpha}°))/(sen({c.beta}°+{est.delta}°)·sen({c.beta}°+{c.alpha}°))])²] = <b>{k_val:.5f}</b>", st_formula))
            elif c.metodo == 'Rankine':
                signo = '-' if c.condicion == 'activa' else '+'
                signo_den = '+' if c.condicion == 'activa' else '-'
                story.append(Paragraph(f"<b>Rankine {c.condicion}:</b> K = cos({c.alpha}°)·[cos({c.alpha}°) {signo} √(cos²({c.alpha}°)-cos²({est.phi}°))]/[cos({c.alpha}°) {signo_den} √(cos²({c.alpha}°)-cos²({est.phi}°))] = <b>{k_val:.5f}</b>", st_formula))

            if hay_sismo and c.condicion in ('activa','pasiva'):
                ke = calcular_K_dinamico(est.phi, c.alpha, c.beta, est.delta, c.kh, c.kv)
                ke_eq = (1.0-c.kv)*ke
                nombre_ke = 'KAE' if c.condicion == 'activa' else 'KPE'
                story.append(Paragraph(f"<b>Mononobe-Okabe:</b> {nombre_ke} = <b>{ke:.5f}</b>; coeficiente equivalente (1-kv){nombre_ke} = <b>{ke_eq:.5f}</b>", st_formula))
            story.append(Spacer(1, 10))

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
        
        criticos = []
        for i, f in enumerate(resultado.filas):
            if i == 0:
                criticos.append((f, "Cima del muro"))
                continue
            prev = resultado.filas[i-1]
            if prev.estrato != f.estrato:
                criticos.append((prev, f"Base del Estrato {prev.estrato}"))
                criticos.append((f, f"Cima del Estrato {f.estrato} (Aplica nuevo K)"))
            elif prev.agua == 0 and f.agua > 0:
                criticos.append((f, "Aparición de Nivel Freático"))
            elif i == len(resultado.filas)-1:
                criticos.append((f, f"Base del Muro (Estrato {f.estrato})"))
                
        for f, desc in criticos:
            z_s, sv_s, sh_s = f.z * scale_z, f.sigma_v * scale_p, f.suelo * scale_p
            story.append(Paragraph(f"<b>• z = {z_s:.2f} {lbl_z} ({desc}):</b>", st_body))
            
            detalles_txt = f"<font color='#444444'>Esfuerzo vertical efectivo:</font> σ'_v = {sv_s:.2f} {lbl_p}<br/>"
            
            est = c.estratos[f.estrato-1]
            c_val = est.cohesion * scale_p
            if c_val > 0 and c.condicion == 'activa':
                detalles_txt += f"<font color='#444444'>Presión lateral activa:</font> σh = {sv_s:.2f}×{f.k:.3f} - 2({c_val:.2f})√{f.k:.3f} = <b>{sh_s:.2f} {lbl_p}</b><br/>"
            elif c_val > 0 and c.condicion == 'pasiva':
                detalles_txt += f"<font color='#444444'>Presión lateral pasiva:</font> σh = {sv_s:.2f}×{f.k:.3f} + 2({c_val:.2f})√{f.k:.3f} = <b>{sh_s:.2f} {lbl_p}</b><br/>"
            else:
                detalles_txt += f"<font color='#444444'>Presión lateral del suelo:</font> σh = {sv_s:.2f}×{f.k:.3f} = <b>{sh_s:.2f} {lbl_p}</b><br/>"

            if f.agua > 0:
                detalles_txt += f"<font color='#444444'>Presión de poros:</font> u = <b>{f.agua * scale_p:.2f} {lbl_p}</b><br/>"
            if abs(f.carga) > 1e-10:
                detalles_txt += f"<font color='#444444'>Sobrecargas:</font> Δσh,q = <b>{f.carga * scale_p:.2f} {lbl_p}</b><br/>"
            if abs(f.sismo) > 1e-10:
                detalles_txt += f"<font color='#444444'>Incremento sísmico:</font> Δσh,E = <b>{f.sismo * scale_p:.2f} {lbl_p}</b><br/>"
            story.append(Paragraph(detalles_txt, st_indent))
            story.append(Spacer(1, 4))
            
        story.append(Spacer(1, 10))

        # =========================================================
        # SECCIÓN 4: CÁLCULO DEL EMPUJE TOTAL (ÁREAS)
        # =========================================================
        story.append(Paragraph("4. CÁLCULO DEL EMPUJE TOTAL (Áreas Geométricas)", st_h1))
        story.append(Paragraph("El empuje total se obtiene integrando el diagrama de presiones. Los tramos lineales se descomponen en rectángulos y triángulos; los diagramas no lineales de sobrecargas localizadas se integran numéricamente mediante trapecios.", st_body))
        
        for d in resultado.detalles:
            if abs(d.fuerza * scale_F) > 0.005:
                f_val, h_s, p1_s = d.fuerza * scale_F, d.h_tramo * scale_z, d.p_calc * scale_p
                
                if d.forma == 'Triángulo':
                    f_str = f"({p1_s:.2f} × {h_s:.2f}) / 2"
                elif d.forma == 'Rectángulo':
                    f_str = f"{p1_s:.2f} × {h_s:.2f}"
                else:
                    f_str = f"Fórmula analítica ({d.forma})"
                circle_num = f"E{d.id}"

                story.append(Paragraph(f"<b>• Área {circle_num} ({d.componente} - {d.forma}):</b> {f_str} = <b>{f_val:.2f} {lbl_F}</b>", st_indent))
                
        story.append(Spacer(1, 15))

        # =========================================================
        # SECCIÓN 5: TOTALES
        # =========================================================
        story.append(Paragraph("5. RESUMEN DE COMPONENTES", st_h1))
        datos_res = [["Fuerza Agrupada", f"Fuerza P ({lbl_F})", f"Momento M ({lbl_M})", f"Brazo y ({lbl_z})"]]
        for comp, vals in resultado.componentes.items():
            if abs(vals[0] * scale_F) > 0.005:
                datos_res.append([comp, f"{vals[0]*scale_F:.3f}", f"{vals[1]*scale_F*scale_z:.3f}", f"{vals[2]*scale_z:.3f}"])
        datos_res.append(["SUMATORIA TOTAL", f"{resultado.total*scale_F:.3f}", f"{resultado.momento*scale_F*scale_z:.3f}", f"{resultado.y*scale_z:.3f}"])
        
        t_res = Table(datos_res, colWidths=[140, 110, 120, 110])
        t_res.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1b365d")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e0e0e0")), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t_res)
        
        story.append(PageBreak())

        # =========================================================
        # SECCIÓN 6: GRÁFICO (Nueva página)
        # =========================================================
        story.append(Paragraph("6. DIAGRAMA DE ESFUERZOS HORIZONTALES", st_h1))
        ruta_main = rutas_png.get('principal')
        if ruta_main and os.path.exists(ruta_main):
            story.append(RLImage(ruta_main, width=460, height=360))
            archivos_generados.append(ruta_main)
            
        aislados = [k for k in rutas_png.keys() if k != 'principal']
        if aislados:
            story.append(PageBreak())
            story.append(Paragraph("7. DESGLOSE GRÁFICO POR COMPONENTES", st_h1))
            story.append(Paragraph("A continuación se presentan los diagramas de presiones y líneas de acción aisladas para cada solicitación existente en el análisis:", st_body))
            
            for clave in aislados:
                ruta_iso = rutas_png[clave]
                if os.path.exists(ruta_iso):
                    story.append(Spacer(1, 10))
                    story.append(RLImage(ruta_iso, width=400, height=310))
                    archivos_generados.append(ruta_iso)
            
        doc.build(story)
        archivos_generados.append(ruta_pdf)
        
    except ImportError:
        archivos_generados.append("\n(Aviso: Instala reportlab para generar el PDF)")
        
    return archivos_generados