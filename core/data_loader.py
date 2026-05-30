"""
Load CSVs from data/ into Parameters.
T_travel, G_cost, Apt are built after collapsing to R'_{ijm} (minimum-time route per mode).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import InstanceConfig
from core.parameters import Parameters


def _csv(data_dir: Path, name: str) -> pd.DataFrame:
    path = data_dir / f"{name}.csv"
    df = pd.read_csv(path)
    if df.isnull().any(axis=None).item():
        raise ValueError(f"{name}.csv: contiene NaN")
    return df


def load(config: InstanceConfig) -> Parameters:
    d = config.data_dir

    # --- bodegas_candidatas ---
    bodegas = _csv(d, "bodegas_candidatas").set_index("id_bodega")
    C = bodegas["capacidad_m3"].rename_axis("i")
    F = bodegas["costo_fijo_CLP"].rename_axis("i")
    L = bodegas["personal_min"].rename_axis("i")
    Emax = bodegas["personal_max"].rename_axis("i")
    g_map = {
        "Grande": 3, "Mediana": 2, "Pequeña": 1,
    }
    warehouse_g: pd.Series = bodegas["tamano"].map(g_map).rename_axis("i")

    # --- insumos ---
    insumos = _csv(d, "insumos").set_index("insumo")
    E_vol = insumos["volumen_m3"].rename_axis("k")
    V = insumos["costo_compra_CLP"].rename_axis("k")
    H = insumos["costo_bodegaje_CLP_mes"].rename_axis("k")
    alpha = insumos["alpha_min"].rename_axis("k")
    beta = insumos["beta_min"].rename_axis("k")

    # --- vehiculos ---
    vehiculos = _csv(d, "vehiculos").set_index("vehiculo")
    A = vehiculos["capacidad_m3"].rename_axis("m")
    O = vehiculos["tiempo_operativo_min"].rename_axis("m")

    # --- ponderadores ---
    pond = _csv(d, "ponderadores").set_index("prioridad")
    W = pond["W_p"].rename_axis("p")
    pi = pond["pi_p"].rename_axis("p")

    # --- parametros_globales ---
    glob = _csv(d, "parametros_globales").set_index("param")["valor"]
    rho = float(glob["rho"])
    d_hours = float(glob["d_horas_mes"])
    B = float(glob["presupuesto_B"])
    h = float(glob["factor_h"])
    sueldo = float(glob["sueldo_mensual"])

    # --- flota_disponible ---
    flota = _csv(d, "flota_disponible")
    Q: pd.Series = flota.set_index(["vehiculo", "mes"])[
        "cantidad_max"].rename_axis(["m", "t"])

    # --- stock_inicial ---
    s0_df = _csv(d, "stock_inicial")
    S0: pd.Series = s0_df.set_index(["id_bodega", "insumo"])[
        "stock_inicial"].rename_axis(["i", "k"])

    # --- demanda_proyectada ---
    dem = _csv(d, "demanda_proyectada")
    D: pd.Series = dem.set_index(["id_comuna", "insumo", "mes", "prioridad"])[
        "cantidad_unidades"].rename_axis(["j", "k", "t", "p"])

    # --- matriz_transporte: collapse to R'_{ijm} (min-time route per mode) ---
    trans = _csv(d, "matriz_transporte")
    # Keep only apt=1 rows, then select minimum-time route per (bodega,
    # comuna, vehiculo)
    trans_apt = trans[trans["aptitud"] == 1].copy()
    idx_min = trans_apt.groupby(["id_bodega", "id_comuna", "vehiculo"])[
        "tiempo_min"].idxmin()
    r_prime = trans_apt.loc[idx_min].set_index(
        ["id_bodega", "id_comuna", "vehiculo"])k

    T_travel: pd.Series = r_prime["tiempo_min"].rename_axis(["i", "j", "m"])
    G_cost: pd.Series = r_prime["costo_viaje_CLP"].rename_axis(["i", "j", "m"])
    # Apt: 1 for all (i,j,m) present in R' (already filtered by apt=1 above)
    Apt: pd.Series = pd.Series(
        1, index=r_prime.index.rename(["i", "j", "m"]), name="aptitud"
    )

    # Validation
    if (C < 0).any():
        raise ValueError("C contiene valores negativos")
    if (D < 0).any():
        raise ValueError("D contiene valores negativos")

    return Parameters(
        D=D, C=C, F=F, E_vol=E_vol, V=V, H=H, S0=S0,
        A=A, O=O, T_travel=T_travel, G_cost=G_cost, Apt=Apt,
        Q=Q, W=W, pi=pi, alpha=alpha, beta=beta,
        L=L, Emax=Emax, warehouse_g=warehouse_g,
        rho=rho, d=d_hours, B=B, h=h, sueldo_mensual=sueldo,
    )
