"""
Módulo de Exportación.
Guarda la tabla de cálculo de resultados detallados en un archivo plano CSV.
"""
import csv

def exportar(resultado, ruta_csv):
    """
    Escribe el desglose de los esfuerzos calculados (punto por punto z) en un archivo .csv.
    """
    # 1. Abrimos el archivo en modo escritura ('w')
    with open(ruta_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';') # Usa punto y coma para separar columnas en Excel
        
        # 2. Escribimos los encabezados (Títulos de las columnas)
        writer.writerow(['z (m)', 'Estrato', 'Sigma_v (efectivo)', 'K_aplicado', 
                         'Presion Suelo', 'Presion Agua', 'Incremento Sobrecarga', 
                         'Incremento Sismo', 'Total Horizontal'])
                         
        # 3. Iterar sobre cada fila calculada en el resultado e imprimir sus valores numéricos
        for fila in resultado.filas:
            writer.writerow([
                f"{fila.z:.4f}",
                fila.estrato,
                f"{fila.sigma_v:.4f}",
                f"{fila.k:.4f}",
                f"{fila.suelo:.4f}",
                f"{fila.agua:.4f}",
                f"{fila.carga:.4f}",
                f"{fila.sismo:.4f}",
                f"{fila.total:.4f}"
            ])
            
    # Retornamos la ruta donde se guardó para mostrárselo al usuario en la ventana emergente
    return [ruta_csv]