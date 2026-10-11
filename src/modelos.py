"""
Módulo de Modelos de Datos.
[V.1.2.1] Incorpora estructuras para empujes laterales del T1 y la verificación de estabilidad del TP.
"""
# [V.1.2.0] Importación de dataclasses para la definición de modelos estructurados
from dataclasses import dataclass, field
# [V.1.2.0] Importación de tipos estáticos para tipado estricto
from typing import List, Optional, Dict

# [V.1.2.0] Estructura de datos para capas de suelo del relleno
@dataclass
class Estrato:
    h: float          # [V.1.2.0] Espesor del estrato (m)
    gamma: float      # [V.1.2.0] Peso específico natural/seco (kN/m³)
    gamma_sat: float  # [V.1.2.0] Peso específico saturado (kN/m³)
    phi: float        # [V.1.2.0] Ángulo de fricción interna (°)
    cohesion: float   # [V.1.2.0] Cohesión efectiva c' (kPa)
    delta: float      # [V.1.2.0] Fricción muro-suelo δ (°)

# [V.1.2.0] Estructura de datos para sobrecargas aplicadas
@dataclass
class Carga:
    tipo: str         # [V.1.2.0] Tipo: 'uniforme', 'franja', 'lineal', 'puntual'
    magnitud: float   # [V.1.2.0] Magnitud de la sobrecarga (kPa o kN/m)
    a: float          # [V.1.2.0] Distancia desde el muro (m)
    b: float          # [V.1.2.0] Ancho de la zona cargada (m)

# [V.2.2.0] Estructura de datos para la geometría de la zapata de cimentación
@dataclass
class DatosZapata:
    B: float           # [V.2.2.0] Ancho total de la base (m)
    b_puntera: float   # [V.2.2.0] Longitud de la puntera/pie (m)
    b_talon: float     # [V.2.2.0] Longitud del talón (m)
    h_zapata: float    # [V.2.2.0] Peralte de la zapata (m)
    df: float          # [V.2.2.0] Profundidad de desplante (m)
    delta_base: float  # [V.2.2.0] Fricción base-suelo (°)
    q_adm: float       # [V.2.2.0] Capacidad portante admisible (kPa)

# [V.1.2.1] Objeto principal del problema físico a evaluar
@dataclass
class Caso:
    altura: float                 # [V.1.2.0] Altura total del muro (m)
    estratos: List[Estrato]       # [V.1.2.0] Lista de estratos de suelo
    condicion: str                # [V.1.2.0] 'activa', 'pasiva' o 'reposo'
    metodo: str                   # [V.1.2.0] 'Rankine', 'Coulomb' o 'Jaky'
    z_agua: Optional[float]       # [V.1.2.0] Profundidad del Nivel Freático (m)
    gamma_agua: float             # [V.1.2.0] Peso específico del agua (kN/m³)
    alpha: float                  # [V.1.2.0] Inclinación del relleno α (°)
    beta: float                   # [V.1.2.0] Inclinación de la cara del muro β (°)
    kh: float                     # [V.1.2.0] Coeficiente sísmico horizontal
    kv: float                     # [V.1.2.0] Coeficiente sísmico vertical
    cargas: List[Carga]           # [V.1.2.0] Lista de sobrecargas externas
    zapata: Optional[DatosZapata] = None  # [V.2.2.0] Geometría de zapata agregada para V2

# [V.1.2.0] Fila discreta del perfil de presiones
@dataclass
class FilaResultado:
    z: float          # [V.1.2.0] Coordenada de profundidad (m)
    estrato: int      # [V.1.2.0] Índice del estrato
    sigma_v: float    # [V.1.2.0] Esfuerzo vertical efectivo (kPa)
    k: float          # [V.1.2.0] Coeficiente de empuje (Ka, Kp, K0)
    suelo: float      # [V.1.2.0] Presión lateral del suelo (kPa)
    agua: float       # [V.1.2.0] Presión de poros (kPa)
    carga: float      # [V.1.2.0] Presión por sobrecarga (kPa)
    sismo: float      # [V.1.2.0] Incremento sísmico (kPa)
    total: float      # [V.1.2.0] Presión lateral total actuante (kPa)
    carga_inf: float = 0.0  # [V.1.2.0] Separador para sobrecargas infinitas

# [V.1.2.0] Polígono geométrico derivado del perfil de presiones
@dataclass
class AreaDetalle:
    id: int           # [V.1.2.0] Identificador numérico
    componente: str   # [V.1.2.0] 'Suelo', 'Agua', 'Sobrecarga', 'Sismo'
    forma: str        # [V.1.2.0] 'Triángulo', 'Rectángulo'
    fuerza: float     # [V.1.2.0] Fuerza resultante (kN/m)
    z_centro: float   # [V.1.2.0] Coordenada z del centroide (m)
    y_base: float     # [V.1.2.0] Brazo de palanca respecto a la base (m)
    p_centro: float   # [V.1.2.0] Presión centroidal (kPa)
    p_calc: float = 0.0   # [V.1.2.0] Presión base para cálculo
    h_tramo: float = 0.0  # [V.1.2.0] Altura del tramo geométrico

# [V.2.2.0] Estructura de resultados para la verificación de estabilidad geotécnica
@dataclass
class ResultadoEstabilidad:
    W_muro: float          # [V.2.2.0] Peso propio del concreto (kN/m)
    W_suelo: float         # [V.2.2.0] Peso del suelo sobre el talón (kN/m)
    M_resistente: float    # [V.2.2.0] Momento resistente total (kN·m/m)
    M_actuante: float      # [V.2.2.0] Momento volcante total (kN·m/m)
    FS_volteo: float       # [V.2.2.0] Factor de seguridad contra volteo
    FS_deslizamiento: float # [V.2.2.0] Factor de seguridad contra deslizamiento
    excentricidad: float   # [V.2.2.0] Excentricidad e (m)
    e_max: float           # [V.2.2.0] Excentricidad máxima admisible B/6 (m)
    q_max: float           # [V.2.2.0] Presión máxima en la punta (kPa)
    q_min: float           # [V.2.2.0] Presión mínima en el talón (kPa)
    q_ult: float           # [V.2.2.0] Capacidad portante última (kPa)
    FS_capacidad: float    # [V.2.2.0] Factor de seguridad por capacidad de carga
    cumple_volteo: bool
    cumple_deslizamiento: bool
    cumple_excentricidad: bool
    cumple_capacidad: bool

# [V.1.2.1] Contenedor global con el resultado del análisis
@dataclass
class Resultado:
    caso: Caso                                # [V.1.2.0] Objeto con el caso ingresado
    filas: List[FilaResultado]                # [V.1.2.0] Lista con perfil discreto
    total: float                              # [V.1.2.0] Empuje lateral total (kN/m)
    momento: float                            # [V.1.2.0] Momento volcante (kN·m/m)
    y: float                                  # [V.1.2.0] Punto de aplicación (m)
    componentes: Dict[str, tuple]             # [V.1.2.0] Sumatorias por componente
    detalles: List[AreaDetalle] = field(default_factory=list) # [V.1.2.0] Áreas desglosadas
    notas: List[str] = field(default_factory=list)            # [V.1.2.0] Alertas numéricas
    estabilidad: Optional[ResultadoEstabilidad] = None  # [V.2.2.0] Integración de estabilidad TP

# [V.2.2.0] Bloque gravitacional para análisis de pesos y momentos
@dataclass
class CargaVertical:
    nombre: str      # [V.2.2.0] Identificador del componente
    peso: float      # [V.2.2.0] Fuerza gravitacional (kN/m)
    brazo_x: float   # [V.2.2.0] Brazo horizontal desde el punto de giro (m)

# [V.2.2.0] Parámetros resistentes de la superficie de desplante
@dataclass
class SueloCimentacion:
    phi_base: float  # [V.2.2.0] Ángulo de fricción de la base (°)
    c_base: float    # [V.2.2.0] Adhesión o cohesión de la base (kPa)
    k1: float = 0.67 # [V.2.2.0] Coeficiente de reducción de fricción
    k2: float = 0.67 # [V.2.2.0] Coeficiente de reducción de cohesión