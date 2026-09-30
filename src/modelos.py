"""
Módulo de Modelos de Datos.
Incorpora campos para el almacenamiento separado de cargas infinitas y finitas,
permitiendo dibujar el bulbo curvo de Boussinesq sin alterar la integración de Jarquio.
"""
# Importa herramientas de 'dataclasses' para generar clases contenedoras de información de forma automática y limpia
from dataclasses import dataclass, field
# Importa la librería 'typing' para especificar exactamente qué tipo de datos van en listas, diccionarios o si son opcionales
from typing import List, Optional, Dict

# El decorador @dataclass crea automáticamente el constructor (__init__) para la clase que está abajo
@dataclass
class Estrato:
    # Altura o espesor individual de esta capa de suelo
    h: float          
    # Peso específico natural o en estado seco del suelo
    gamma: float      
    # Peso específico saturado del suelo (se utilizará solo si el agua lo inunda)
    gamma_sat: float  
    # Ángulo de fricción interna efectiva del suelo (φ')
    phi: float        
    # Cohesión efectiva del suelo (c')
    cohesion: float   
    # Ángulo de fricción en la interfaz entre el suelo y el muro (δ)
    delta: float      

@dataclass
class Carga:
    # Identifica si la sobrecarga es 'uniforme' (infinita), 'franja' (finita), 'lineal' o 'puntual'
    tipo: str         
    # Valor numérico de la carga impuesta (puede ser presión, fuerza por metro o fuerza concentrada)
    magnitud: float   
    # Distancia libre desde la parte posterior del muro hasta donde comienza a actuar la carga
    a: float          
    # Ancho de la zona cargada (este parámetro solo es relevante para cargas de franja)
    b: float          

@dataclass
class Caso:
    # Altura total (H) geométrica del muro a ser evaluado
    altura: float                 
    # Una lista (arreglo) que contendrá todos los objetos de la clase 'Estrato' creados por el usuario
    estratos: List[Estrato]       
    # Régimen o estado de empuje a evaluar: 'activa', 'pasiva' o 'reposo'
    condicion: str                
    # Teoría geotécnica seleccionada para la resolución: 'Rankine', 'Coulomb' o 'Jaky'
    metodo: str                   
    # Profundidad a la que aparece el Nivel Freático (Optional significa que puede ser un número o no existir [None])
    z_agua: Optional[float]       
    # Peso específico del agua que variará según las unidades seleccionadas por el usuario (ej: 9.81, 1000, 62.4)
    gamma_agua: float             
    # Ángulo de inclinación de la superficie superior del relleno de tierra respecto a la horizontal (α)
    alpha: float                  
    # Ángulo de inclinación de la cara posterior del muro de contención respecto a la horizontal (β)
    beta: float                   
    # Coeficiente de aceleración sísmica horizontal (para usar en Mononobe-Okabe)
    kh: float                     
    # Coeficiente de aceleración sísmica vertical
    kv: float                     
    # Lista de todos los objetos de la clase 'Carga' que se han añadido al terreno
    cargas: List[Carga]           

@dataclass
class FilaResultado:
    # Coordenada de profundidad (z) exacta en la que se evaluaron los datos de esta fila
    z: float          
    # Número de ID secuencial que indica a qué estrato pertenece el suelo a esta profundidad
    estrato: int      
    # Esfuerzo vertical efectivo (σ'v) acumulado por el peso de la tierra y descontando flotación
    sigma_v: float    
    # Coeficiente estático de empuje de tierras (Ka, Kp o K0) obtenido en esta profundidad
    k: float          
    # Esfuerzo lateral resultante generado únicamente por la tierra (empuje de suelo - cohesión)
    suelo: float      
    # Presión lateral generada por los poros de agua (hidrostática)
    agua: float       
    # Esfuerzo lateral resultante que aportan de forma sumada TODAS las sobrecargas externas
    carga: float      
    # Incremento neto de la presión lateral causado exclusivamente por el sismo
    sismo: float      
    # Sumatoria bruta de todos los esfuerzos actuando en esta coordenada z
    total: float      
    # Nuevo campo creado para aislar matemáticamente las cargas infinitas (uniformes) de las finitas (Boussinesq).
    # Se inicializa por defecto en 0.0 para compatibilidad con código heredado si no se envía este dato.
    carga_inf: float = 0.0  

@dataclass
class AreaDetalle:
    # Número secuencial (1, 2, 3...) asignado a la figura geométrica extraída
    id: int           
    # Nombre del componente que originó esta área ('Suelo', 'Agua', 'Sobrecarga', 'Sismo')
    componente: str   
    # Clasificación geométrica del bloque de esfuerzo ('Rectángulo', 'Triángulo', 'Bulbo Boussinesq', etc.)
    forma: str        
    # Magnitud de la fuerza de empuje representada por el área de esta figura
    fuerza: float     
    # Coordenada 'z' donde recae el centro de gravedad (centroide) medido desde la cima del muro
    z_centro: float   
    # Brazo de palanca (y) de esta fuerza respecto al nivel de zapata o base del muro
    y_base: float     
    # Presión de la figura en su centroide, usada gráficamente para no superponer los círculos de numeración con los límites
    p_centro: float   
    # Esfuerzo base principal usado para documentar textualmente la fórmula del área en el PDF (por defecto es 0)
    p_calc: float = 0.0  
    # Altura del tramo (Δz) involucrado en la figura para documentar su área en el PDF (por defecto es 0)
    h_tramo: float = 0.0 

@dataclass
class Resultado:
    # Se incrusta el objeto 'Caso' completo para no perder la información origen y el contexto del problema
    caso: Caso                                
    # Array inmenso que guarda todas las evaluaciones milímetro a milímetro (Lista de objetos 'FilaResultado')
    filas: List[FilaResultado]                
    # Magnitud de la Resultante Total del empuje (sumatoria de todo el sistema)
    total: float                              
    # Magnitud del Momento Total de volcamiento en la base del muro
    momento: float                            
    # Brazo de palanca definitivo de la Fuerza Resultante Total (y_T)
    y: float                                  
    # Un diccionario para aislar rápidamente la macro-resultante de cada fenómeno natural:
    # Ej: {'Suelo': (Fuerza, Momento, y), 'Agua': (Fuerza, Momento, y)}
    componentes: Dict[str, tuple]             
    # Lista de figuras geométricas cortadas de los diagramas de presión (Lista de objetos 'AreaDetalle').
    # Se usa 'field(default_factory=list)' para inicializarla de manera segura y vacía si la llamada no la proporciona.
    detalles: List[AreaDetalle] = field(default_factory=list) 
    # Lista de mensajes de texto (advertencias y anotaciones metodológicas) para imprimir al usuario y anexar al PDF final.
    notas: List[str] = field(default_factory=list)