"""
Generate synthetic data for SENAPRED logistics model.
All ranges are justified in E3/main.tex §"Origen de los Datos".
Run: python scripts/generate_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import InstanceConfig


def generate(config: InstanceConfig | None = None) -> None:
    cfg = config or InstanceConfig()
    rng = np.random.default_rng(cfg.seed)
    out = cfg.data_dir
    out.mkdir(exist_ok=True)

    I = list(cfg.I)
    J = list(cfg.J)
    K = list(cfg.K)
    M = list(cfg.M)
    T = list(cfg.T)
    P = list(cfg.P)

    def _write(df: pd.DataFrame, name: str) -> None:
        df.to_csv(out / f"{name}.csv", index=False)

    # --- C_i: capacidad bodega [m³] — galpones 1000–8000 m³ (ChileCompra)
    c_vals = rng.integers(1000, 8001, size=len(I))
    _write(pd.DataFrame({"i": I, "value": c_vals}), "capacidad_bodega")

    # --- warehouse_g: categoría por tamaño
    # i=0 pequeña(g=1), i=1 mediana(g=2), i=2 grande(g=3)
    _write(pd.DataFrame({"i": I, "value": cfg.warehouse_sizes}), "warehouse_g")

    # --- F_i: costo fijo apertura [CLP] — arriendo 10–60 MM/mes → costo apertura único
    # Interpretamos F_i como costo fijo único = 3 meses de arriendo (periodo de setup)
    monthly_rent = rng.integers(10_000_000, 60_000_001, size=len(I))
    f_vals = monthly_rent * 3
    _write(pd.DataFrame({"i": I, "value": f_vals}), "costo_apertura")

    # --- E_k: volumen unitario [m³/unidad]
    # agua: 0.001 m³/L (contenedor 5L), alimentos: 0.003, medicamentos: 0.001,
    # frazadas: 0.015, baterias: 0.002, radios: 0.001, higiene: 0.002
    e_map: dict[str, float] = {
        "agua": 0.001,
        "alimentos": 0.003,
        "medicamentos": 0.001,
        "frazadas": 0.015,
        "baterias": 0.002,
        "radios": 0.001,
        "higiene": 0.002,
    }
    _write(
        pd.DataFrame({"k": list(e_map.keys()), "value": list(e_map.values())}),
        "volumen_insumo",
    )

    # --- V_{kt}: costo compra [CLP/unidad], varía por mes (±10%)
    rows_v: list[dict[str, object]] = []
    base_v: dict[str, float] = {
        "agua": 1_500.0,
        "alimentos": 3_200.0,
        "medicamentos": 8_500.0,
        "frazadas": 12_000.0,
        "baterias": 15_000.0,
        "radios": 45_000.0,
        "higiene": 2_500.0,
    }
    for k in K:
        for t in T:
            factor = 1.0 + rng.uniform(-0.10, 0.10)
            rows_v.append({"k": k, "t": t, "value": round(base_v[k] * factor, 2)})
    _write(pd.DataFrame(rows_v), "costo_compra")

    # --- H_{ikt}: costo mantención [CLP/(unidad·mes)] ≈ 5% de V_{kt}
    rows_h: list[dict[str, object]] = []
    v_df = pd.DataFrame(rows_v).set_index(["k", "t"])["value"]
    for i in I:
        for k in K:
            for t in T:
                rows_h.append(
                    {"i": i, "k": k, "t": t, "value": round(float(v_df[(k, t)]) * 0.05, 2)}
                )
    _write(pd.DataFrame(rows_h), "costo_mantencion")

    # --- A_m: capacidad carga [m³]
    a_map: dict[str, float] = {
        "camion": 30.0,
        "camioneta": 3.0,
        "ambulancia": 2.0,
        "helicoptero": 2.0,
        "avioneta": 5.0,
    }
    _write(
        pd.DataFrame({"m": list(a_map.keys()), "value": list(a_map.values())}),
        "capacidad_vehiculo",
    )

    # --- T_travel_{ijmt}: tiempo transporte [min] — distancias inter-comuna 5–80 km / velocidades
    # velocidad terrestre: 65 km/h, aéreo: 150 km/h; O_m incluido aparte
    dist_km: dict[tuple[int, int], float] = {}
    for i in I:
        for j in J:
            dist_km[(i, j)] = float(rng.uniform(5.0, 80.0))

    rows_t: list[dict[str, object]] = []
    speed: dict[str, float] = {
        "camion": 60.0,
        "camioneta": 65.0,
        "ambulancia": 70.0,
        "helicoptero": 150.0,
        "avioneta": 200.0,
    }
    for i in I:
        for j in J:
            d = dist_km[(i, j)]
            for m in M:
                base_t = (d / speed[m]) * 60.0
                for t in T:
                    # pequeña variación estacional (±5%)
                    factor = 1.0 + rng.uniform(-0.05, 0.05)
                    rows_t.append({"i": i, "j": j, "m": m, "t": t, "value": round(base_t * factor, 2)})
    _write(pd.DataFrame(rows_t), "tiempo_transporte")

    # --- O_m: tiempo preparación [min] (MOP)
    o_map: dict[str, float] = {
        "camion": 30.0,
        "camioneta": 15.0,
        "ambulancia": 10.0,
        "helicoptero": 45.0,
        "avioneta": 60.0,
    }
    _write(
        pd.DataFrame({"m": list(o_map.keys()), "value": list(o_map.values())}),
        "tiempo_preparacion",
    )

    # --- G_{ijm}: costo operativo por viaje [CLP/viaje]
    rows_g: list[dict[str, object]] = []
    cost_per_km: dict[str, float] = {
        "camion": 800.0,
        "camioneta": 500.0,
        "ambulancia": 600.0,
        "helicoptero": 8_000.0,
        "avioneta": 6_000.0,
    }
    for i in I:
        for j in J:
            d = dist_km[(i, j)]
            for m in M:
                rows_g.append({"i": i, "j": j, "m": m, "value": round(d * cost_per_km[m], 2)})
    _write(pd.DataFrame(rows_g), "costo_viaje")

    # --- W_p: ponderadores urgencia W1>W2>W3
    _write(pd.DataFrame({"p": P, "value": [100.0, 10.0, 1.0]}), "ponderador_prioridad")

    # --- S0_{ik}: stock inicial
    rows_s0: list[dict[str, object]] = []
    for i in I:
        for k in K:
            rows_s0.append({"i": i, "k": k, "value": int(rng.integers(0, 51))})
    _write(pd.DataFrame(rows_s0), "stock_inicial")

    # --- alpha_k, beta_k: 5–15 s/unidad → min/unidad
    rows_ab: list[dict[str, object]] = []
    for k in K:
        a_s = rng.uniform(5.0, 15.0)
        b_s = rng.uniform(5.0, 15.0)
        rows_ab.append({"k": k, "alpha": round(a_s / 60.0, 5), "beta": round(b_s / 60.0, 5)})
    _write(pd.DataFrame(rows_ab), "tiempos_manipulacion")

    # --- rho, d (escalares en CSV de parámetros globales)
    _write(
        pd.DataFrame({"param": ["rho", "d", "h", "B"], "value": [0.75, 160.0, 1e-7, 3_000_000_000.0]}),
        "parametros_globales",
    )

    # --- L_g, Emax_g: dotación personal
    _write(
        pd.DataFrame({"g": list(cfg.warehouse_sizes), "value": [2, 4, 8]}),
        "dotacion_minima",
    )
    _write(
        pd.DataFrame({"g": list(cfg.warehouse_sizes), "value": [5, 12, 25]}),
        "dotacion_maxima",
    )

    # --- Omega_t: costo personal [CLP/(persona·mes)]
    rows_om: list[dict[str, object]] = []
    for t in T:
        rows_om.append({"t": t, "value": round(float(rng.integers(800_000, 1_200_001)), 2)})
    _write(pd.DataFrame(rows_om), "costo_personal")

    # --- Apt_{mj}: aptitud vehículo para ruta a comuna j
    # Terrestres aptos para todas; aéreos aptos donde terrestre tarda >T^max_2
    # Se calcula a posteriori en sets.py usando T_travel; aquí se guarda la tabla base
    rows_apt: list[dict[str, object]] = []
    terrestres = {"camion", "camioneta", "ambulancia"}
    aereos = {"helicoptero", "avioneta"}
    for m in M:
        for j in J:
            if m in terrestres:
                # camión no apto en comunas de cerro (j=3 Valparaíso, j=0 Viña → cerros)
                if m == "camion" and j in (0, 3):
                    apt = int(rng.choice([0, 1], p=[0.4, 0.6]))
                else:
                    apt = 1
            else:  # aéreos
                apt = 1
            rows_apt.append({"m": m, "j": j, "value": apt})
    _write(pd.DataFrame(rows_apt), "aptitud_vehiculo")

    # --- Q_{mt}: pool vehicular disponible
    q_base: dict[str, int] = {
        "camion": 4,
        "camioneta": 8,
        "ambulancia": 3,
        "helicoptero": 2,
        "avioneta": 2,
    }
    rows_q: list[dict[str, object]] = []
    for m in M:
        for t in T:
            rows_q.append({"m": m, "t": t, "value": q_base[m]})
    _write(pd.DataFrame(rows_q), "pool_vehicular")

    # --- D_{jktp}: demanda proyectada, solo en fire_months
    # 78% concentrado en Viña(0), Quilpué(1), Villa Alemana(2) — FIBE
    fire_months = list(cfg.fire_months)
    rows_d: list[dict[str, object]] = []
    base_demand: dict[str, int] = {
        "agua": 5000,
        "alimentos": 3000,
        "medicamentos": 800,
        "frazadas": 2000,
        "baterias": 500,
        "radios": 300,
        "higiene": 1500,
    }
    # peso por comuna: 78% entre j=0,1,2; 22% entre j=3,4
    commune_weight = [0.30, 0.26, 0.22, 0.14, 0.08]
    for j in J:
        for k in K:
            p_supply = cfg.priority_of_supply[k]
            for t in fire_months:
                d_base = base_demand[k] * commune_weight[j]
                noise = rng.uniform(0.8, 1.2)
                # demanda positiva solo en prioridad asignada al insumo
                for p in P:
                    if p == p_supply:
                        rows_d.append({"j": j, "k": k, "t": t, "p": p, "value": round(d_base * noise)})
                    else:
                        rows_d.append({"j": j, "k": k, "t": t, "p": p, "value": 0.0})
    _write(pd.DataFrame(rows_d), "demanda")

    # --- pi_p: penalización faltante [min-equiv/unidad]
    _write(pd.DataFrame({"p": P, "value": [10000.0, 1000.0, 100.0]}), "penalizacion_faltante")

    print(f"[generate_data] CSV escritos en {out}/")


if __name__ == "__main__":
    generate()
