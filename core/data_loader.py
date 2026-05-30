"""
Load CSV data from data/ into Parameters dataclass.
Each CSV is tidy (long-format): index columns + "value".
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import InstanceConfig
from core.parameters import Parameters


def _series(path: Path, idx_cols: list[str]) -> pd.Series:
    df = pd.read_csv(path)
    missing = [c for c in idx_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")
    if df["value"].isna().any():
        raise ValueError(f"{path.name}: NaN values found")
    return df.set_index(idx_cols)["value"]


def load(config: InstanceConfig) -> Parameters:
    d = config.data_dir

    def p(name: str) -> Path:
        return d / f"{name}.csv"

    # Scalars from parametros_globales
    glob = pd.read_csv(p("parametros_globales")).set_index("param")["value"]
    rho = float(glob["rho"])
    d_hours = float(glob["d"])
    h = float(glob["h"])
    B = float(glob["B"])

    # Validate non-negativity on key series
    C = _series(p("capacidad_bodega"), ["i"])
    F = _series(p("costo_apertura"), ["i"])
    E_vol = _series(p("volumen_insumo"), ["k"])
    V = _series(p("costo_compra"), ["k", "t"])
    H = _series(p("costo_mantencion"), ["i", "k", "t"])
    A = _series(p("capacidad_vehiculo"), ["m"])
    T_travel = _series(p("tiempo_transporte"), ["i", "j", "m", "t"])
    O = _series(p("tiempo_preparacion"), ["m"])
    G_cost = _series(p("costo_viaje"), ["i", "j", "m"])
    W = _series(p("ponderador_prioridad"), ["p"])
    S0 = _series(p("stock_inicial"), ["i", "k"])
    ab_df = pd.read_csv(p("tiempos_manipulacion"))
    alpha: pd.Series = ab_df.set_index("k")["alpha"]
    beta: pd.Series = ab_df.set_index("k")["beta"]
    L = _series(p("dotacion_minima"), ["g"])
    Emax = _series(p("dotacion_maxima"), ["g"])
    Omega = _series(p("costo_personal"), ["t"])
    Apt = _series(p("aptitud_vehiculo"), ["m", "j"])
    Q = _series(p("pool_vehicular"), ["m", "t"])
    D = _series(p("demanda"), ["j", "k", "t", "p"])
    pi = _series(p("penalizacion_faltante"), ["p"])
    warehouse_g = _series(p("warehouse_g"), ["i"])

    # Range validations
    for s, name in [(C, "C"), (F, "F"), (E_vol, "E_vol"), (A, "A")]:
        if (s < 0).any():
            raise ValueError(f"{name} has negative values")

    return Parameters(
        D=D,
        C=C,
        E_vol=E_vol,
        F=F,
        V=V,
        H=H,
        A=A,
        B=B,
        T_travel=T_travel,
        O=O,
        G_cost=G_cost,
        W=W,
        S0=S0,
        alpha=alpha,
        beta=beta,
        rho=rho,
        d=d_hours,
        L=L,
        Emax=Emax,
        Omega=Omega,
        Apt=Apt,
        Q=Q,
        h=h,
        pi=pi,
        warehouse_g=warehouse_g,
    )
