"""
Módulo de Modelos de Datos.
Incorpora campos para almacenar las variables geométricas base (p_calc y h_tramo)
y así poder imprimir las fórmulas de áreas explícitamente en el PDF.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class Estrato:
    h: float          
    gamma: float      
    gamma_sat: float  
    phi: float        
    cohesion: float   
    delta: float      

@dataclass
class Carga:
    tipo: str         
    magnitud: float   
    a: float          
    b: float          

@dataclass
class Caso:
    altura: float                 
    estratos: List[Estrato]       
    condicion: str                
    metodo: str                   
    z_agua: Optional[float]       
    gamma_agua: float             
    alpha: float                  
    beta: float                   
    kh: float                     
    kv: float                     
    cargas: List[Carga]           

@dataclass
class FilaResultado:
    z: float          
    estrato: int      
    sigma_v: float    
    k: float          
    suelo: float      
    agua: float       
    carga: float      
    sismo: float      
    total: float      

@dataclass
class AreaDetalle:
    id: int           
    componente: str   
    forma: str        
    fuerza: float     
    z_centro: float   
    y_base: float     
    p_centro: float   
    p_calc: float = 0.0  # Presión base para la fórmula visual
    h_tramo: float = 0.0 # Altura geométrica para la fórmula visual

@dataclass
class Resultado:
    caso: Caso                                
    filas: List[FilaResultado]                
    total: float                              
    momento: float                            
    y: float                                  
    componentes: Dict[str, tuple]             
    detalles: List[AreaDetalle] = field(default_factory=list) 
    notas: List[str] = field(default_factory=list)