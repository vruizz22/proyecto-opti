from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Parameters:
    # D_{jktp}: demanda proyectada [unidades]  index=(j,k,t,p)
    D: pd.Series

    # C_i: capacidad max bodega [m³]  index=(i,)
    C: pd.Series

    # E_k: volumen unitario [m³/unidad]  index=(k,)
    E_vol: pd.Series

    # F_i: costo fijo apertura [CLP]  index=(i,)
    F: pd.Series

    # V_{kt}: costo compra [CLP/unidad]  index=(k,t)
    V: pd.Series

    # H_{ikt}: costo mantención [CLP/(unidad·mes)]  index=(i,k,t)
    H: pd.Series

    # A_m: capacidad carga vehículo [m³]  index=(m,)
    A: pd.Series

    # B: presupuesto total [CLP]
    B: float

    # T_{ijmt}: tiempo transporte [min]  index=(i,j,m,t)   (r colapsado a singleton)
    T_travel: pd.Series

    # O_m: tiempo preparación [min]  index=(m,)
    O: pd.Series

    # G_{ijm}: costo operativo por viaje [CLP/viaje]  index=(i,j,m)
    G_cost: pd.Series

    # W_p: ponderador urgencia  index=(p,)
    W: pd.Series

    # S0_{ik}: stock inicial  index=(i,k)
    S0: pd.Series

    # alpha_k, beta_k: tiempos carga/descarga [min/unidad]  index=(k,)
    alpha: pd.Series
    beta: pd.Series

    # rho: factor eficiencia
    rho: float

    # d: horas operativas/mes
    d: float

    # L_g: dotación mínima  index=(g,)
    L: pd.Series

    # Emax_g: dotación máxima  index=(g,)
    Emax: pd.Series

    # Omega_t: costo personal [CLP/(persona·mes)]  index=(t,)
    Omega: pd.Series

    # Apt_{mj}: aptitud vehículo para la ruta a j  index=(m,j)  (r colapsado)
    Apt: pd.Series

    # Q_{mt}: pool vehicular [vehículos]  index=(m,t)
    Q: pd.Series

    # h: factor conversión costo-tiempo [min/CLP]
    h: float

    # pi_p: penalización faltante [min-equiv/unidad]  index=(p,)
    pi: pd.Series

    # warehouse_size_category: g para cada i  index=(i,)
    warehouse_g: pd.Series
