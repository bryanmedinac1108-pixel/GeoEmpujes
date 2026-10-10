"""
Módulo de Modelos de Datos.
[V.1.0] Incorpora campos para el almacenamiento separado de cargas infinitas y finitas.
[V.2.0] Incorpora clases para los pesos de la zapata y el suelo de cimentación.
"""
# [V.1.0] Importa herramientas para generar clases contenedoras de información de forma automática
from dataclasses import dataclass, field
# [V.1.0] Importa la librería 'typing' para especificar tipos de datos (Listas, Opcionales, Diccionarios)
from typing import List, Optional, Dict

# [V.1.0] Crea la clase contenedora para las propiedades de cada capa de suelo del cerro
@dataclass
class Estrato:
    # [V.1.0] Altura o espesor individual de esta capa de suelo
    h: float          
    # [V.1.0] Peso específico natural o en estado seco del suelo
    gamma: float      
    # [V.1.0] Peso específico saturado del suelo (para debajo del Nivel Freático)
    gamma_sat: float  
    # [V.1.0] Ángulo de fricción interna efectiva del suelo (φ')
    phi: float        
    # [V.1.0] Cohesión efectiva del suelo (c')
    cohesion: float   
    # [V.1.0] Ángulo de fricción en la interfaz entre el suelo y el muro (δ)
    delta: float      

# [V.1.0] Crea la clase contenedora para cualquier sobrecarga externa
@dataclass
class Carga:
    # [V.1.0] Identifica si la sobrecarga es 'uniforme', 'franja', 'lineal' o 'puntual'
    tipo: str         
    # [V.1.0] Valor numérico de la carga impuesta
    magnitud: float   
    # [V.1.0] Distancia libre desde la parte posterior del muro hasta la carga (a)
    a: float          
    # [V.1.0] Ancho de la zona cargada (b)
    b: float          

# [V.1.0] Crea la clase que envuelve TODO el problema físico a resolver
@dataclass
class Caso:
    # [V.1.0] Altura total geométrica del muro
    altura: float                 
    # [V.1.0] Arreglo que contiene todos los estratos
    estratos: List[Estrato]       
    # [V.1.0] Condición de empuje: 'activa', 'pasiva' o 'reposo'
    condicion: str                
    # [V.1.0] Teoría geotécnica seleccionada: 'Rankine', 'Coulomb' o 'Jaky'
    metodo: str                   
    # [V.1.0] Profundidad a la que aparece el Nivel Freático
    z_agua: Optional[float]       
    # [V.1.0] Peso específico del agua
    gamma_agua: float             
    # [V.1.0] Ángulo de inclinación de la superficie del relleno (α)
    alpha: float                  
    # [V.1.0] Ángulo de inclinación del muro (β)
    beta: float                   
    # [V.1.0] Coeficiente de aceleración sísmica horizontal
    kh: float                     
    # [V.1.0] Coeficiente de aceleración sísmica vertical
    kv: float                     
    # [V.1.0] Arreglo con todas las sobrecargas añadidas
    cargas: List[Carga]           

# [V.1.0] Fila matemática que guarda los resultados de empujes milímetro a milímetro
@dataclass
class FilaResultado:
    # [V.1.0] Coordenada de profundidad (z) exacta
    z: float          
    # [V.1.0] Número de ID del estrato a esta profundidad
    estrato: int      
    # [V.1.0] Esfuerzo vertical efectivo (σ'v)
    sigma_v: float    
    # [V.1.0] Coeficiente estático de empuje de tierras (Ka, Kp o K0)
    k: float          
    # [V.1.0] Esfuerzo lateral generado por la tierra
    suelo: float      
    # [V.1.0] Presión de poros de agua
    agua: float       
    # [V.1.0] Esfuerzo aportado por sobrecargas
    carga: float      
    # [V.1.0] Incremento de presión por sismo
    sismo: float      
    # [V.1.0] Sumatoria de todos los esfuerzos actuantes
    total: float      
    # [V.1.0] Campo para aislar cargas uniformes de las elásticas (Boussinesq)
    carga_inf: float = 0.0  

# [V.1.0] Define los polígonos gráficos extraídos para la Memoria de Cálculo PDF
@dataclass
class AreaDetalle:
    # [V.1.0] Número secuencial asignado a la figura geométrica
    id: int           
    # [V.1.0] Nombre del componente ('Suelo', 'Agua', 'Sobrecarga', 'Sismo')
    componente: str   
    # [V.1.0] Forma geométrica ('Rectángulo', 'Triángulo')
    forma: str        
    # [V.1.0] Magnitud de la fuerza representada por esta área
    fuerza: float     
    # [V.1.0] Coordenada Z del centro de gravedad
    z_centro: float   
    # [V.1.0] Brazo de palanca (y) respecto a la base del muro
    y_base: float     
    # [V.1.0] Presión en el centroide para colocar el número gráfico
    p_centro: float   
    # [V.1.0] Esfuerzo base para fórmulas de texto
    p_calc: float = 0.0  
    # [V.1.0] Altura del tramo para fórmulas de texto
    h_tramo: float = 0.0 

# [V.1.0] Envoltorio final con todos los resultados de los empujes
@dataclass
class Resultado:
    # [V.1.0] Incrusta el caso original
    caso: Caso                                
    # [V.1.0] Arreglo de todas las filas calculadas
    filas: List[FilaResultado]                
    # [V.1.0] Resultante Total del empuje
    total: float                              
    # [V.1.0] Momento Total de volcamiento
    momento: float                            
    # [V.1.0] Brazo de palanca de la Resultante Total (y_T)
    y: float                                  
    # [V.1.0] Fuerzas separadas por naturaleza (Suelo, Agua, etc.)
    componentes: Dict[str, tuple]             
    # [V.1.0] Lista de figuras geométricas cortadas
    detalles: List[AreaDetalle] = field(default_factory=list) 
    # [V.1.0] Avisos y alertas de cálculo
    notas: List[str] = field(default_factory=list)

# ====================================================================
# [V.2.0] NUEVAS CLASES PARA ESTABILIDAD DE MUROS
# ====================================================================

# [V.2.0] Define los bloques gravitacionales que estabilizan el muro (concreto, tierra arriba)
@dataclass
class CargaVertical:
    # [V.2.0] Nombre identificador (ej: "Zapata", "Pantalla")
    nombre: str      
    # [V.2.0] Peso gravitacional de este bloque en kN/m
    peso: float      
    # [V.2.0] Brazo de palanca horizontal (x) desde la punta de la zapata hasta su centroide
    brazo_x: float   

# [V.2.0] Define las propiedades del terreno sobre el que se apoya la zapata
@dataclass
class SueloCimentacion:
    # [V.2.0] Ángulo de fricción interna del suelo de cimentación
    phi_base: float  
    # [V.2.0] Cohesión del suelo de cimentación
    c_base: float    
    # [V.2.0] Factor de reducción k1 para la fricción muro-suelo (usualmente 2/3)
    k1: float = 0.67 
    # [V.2.0] Factor de reducción k2 para la adhesión muro-suelo (usualmente 2/3)
    k2: float = 0.67