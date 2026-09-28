"""
Módulo de Modelos de Datos.
Define las estructuras que almacenan la información del muro, estratos, cargas y resultados.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class Estrato:
    """Representa una capa de suelo con sus propiedades físicas y mecánicas."""
    h: float          # Espesor del estrato (m)
    gamma: float      # Peso específico natural (kN/m³)
    gamma_sat: float  # Peso específico saturado (kN/m³)
    phi: float        # Ángulo de fricción interna (grados)
    cohesion: float   # Cohesión (kN/m²)
    delta: float      # Ángulo de fricción suelo-muro (grados)

@dataclass
class Carga:
    """Representa una sobrecarga aplicada en la superficie del relleno."""
    tipo: str         # 'uniforme', 'puntual', 'lineal' o 'franja'
    magnitud: float   # Valor de la carga (kN/m², kN/m o kN)
    a: float          # Distancia desde la corona del muro hasta el inicio de la carga (m)
    b: float          # Ancho de la carga (solo aplica para tipo 'franja') (m)

@dataclass
class Caso:
    """Almacena toda la configuración de un análisis específico."""
    altura: float                 # Altura total del muro H (m)
    estratos: List[Estrato]       # Lista de objetos Estrato
    condicion: str                # 'activa', 'pasiva' o 'reposo'
    metodo: str                   # 'Rankine' o 'Coulomb'
    z_agua: Optional[float]       # Profundidad del nivel freático desde la superficie (m). None si no hay agua.
    gamma_agua: float             # Peso específico del agua (normalmente 9.81 kN/m³)
    alpha: float                  # Inclinación del relleno (grados)
    beta: float                   # Inclinación de la cara interna del muro (grados)
    kh: float                     # Coeficiente sísmico horizontal
    kv: float                     # Coeficiente sísmico vertical
    cargas: List[Carga]           # Lista de sobrecargas

@dataclass
class FilaResultado:
    """Representa los esfuerzos calculados a una profundidad específica 'z'."""
    z: float          # Profundidad evaluada (m)
    estrato: int      # Número de estrato (1, 2, 3...)
    sigma_v: float    # Esfuerzo efectivo vertical (kN/m²)
    k: float          # Coeficiente de empuje de tierras evaluado
    suelo: float      # Esfuerzo horizontal debido solo al suelo (kN/m²)
    agua: float       # Presión de poros / hidrostática (kN/m²)
    carga: float      # Incremento de esfuerzo horizontal debido a sobrecargas (kN/m²)
    sismo: float      # Incremento de esfuerzo debido al sismo (kN/m²)
    total: float      # Sumatoria de todos los esfuerzos horizontales en este punto (kN/m²)

@dataclass
class Resultado:
    """Almacena el resultado matemático final para ser mostrado en la interfaz y gráficos."""
    caso: Caso                                # Referencia al caso original evaluado
    filas: List[FilaResultado]                # Lista con el desglose de esfuerzos punto por punto (z)
    total: float                              # Fuerza resultante total P (kN/m)
    momento: float                            # Momento de volcamiento total en la base (kN·m/m)
    y: float                                  # Punto de aplicación de la resultante medido desde la base (m)
    componentes: Dict[str, tuple]             # Diccionario con P, M, y por separado para: Suelo, Agua, Carga, Sismo
    notas: List[str] = field(default_factory=list) # Mensajes de advertencia o aclaraciones del cálculo