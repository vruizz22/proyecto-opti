from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Parameters:
    # Demanda D_{jktp} [unidades]  index=(j,k,t,p)
    D: pd.Series

    # Capacidad bodega C_i [m³]  index=(i,)
    C: pd.Series

    # Costo apertura F_i [CLP]  index=(i,)
    F: pd.Series

    # Volumen unitario E_k [m³/unidad]  index=(k,)
    E_vol: pd.Series

    # Costo compra V_k [CLP/unidad]  index=(k,)
    V: pd.Series

    # Costo mantención H_k [CLP/unidad/mes]  index=(k,)
    H: pd.Series

    # Stock inicial S0_{ik}  index=(i,k)
    S0: pd.Series

    # Capacidad vehículo A_m [m³]  index=(m,)
    A: pd.Series

    # Tiempo operativo O_m [min]  index=(m,)
    O: pd.Series

    # Tiempo viaje mínimo (R' colapsado) T_{ijm} [min]  index=(i,j,m)
    T_travel: pd.Series

    # Costo viaje G_{ijm} [CLP/viaje]  index=(i,j,m)
    G_cost: pd.Series

    # Aptitud Apt_{ijm} ∈ {0,1}  index=(i,j,m)
    Apt: pd.Series

    # Pool vehicular Q_{mt}  index=(m,t)
    Q: pd.Series

    # Ponderadores W_p  index=(p,)
    W: pd.Series

    # Penalización faltante π_p [min-equiv/unidad]  index=(p,)
    pi: pd.Series

    # Tiempos carga/descarga α_k, β_k [min/unidad]  index=(k,)
    alpha: pd.Series
    beta: pd.Series

    # Dotación personal
    L: pd.Series       # personal_min por bodega  index=(i,)
    Emax: pd.Series    # personal_max por bodega  index=(i,)

    # Categoría de tamaño de bodega g  index=(i,)
    warehouse_g: pd.Series

    # Escalares
    rho: float            # factor eficiencia operativa
    d: float              # horas operativas/mes
    B: float              # presupuesto total [CLP]
    h: float              # factor conversión costo→tiempo [min/CLP]
    sueldo_mensual: float  # Ω_t simplificado como constante [CLP/persona/mes]
