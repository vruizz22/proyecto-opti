from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import gurobipy as gp
import pandas as pd

from core.config import InstanceConfig
from core.variables import ModelVars


@dataclass
class Solution:
    obj_value: float
    gap: float
    runtime: float
    status: str
    # DataFrames for reporting
    bodegas: pd.DataFrame       # i, t, y, w, e
    inventario: pd.DataFrame    # i, k, t, s, c
    envios: pd.DataFrame        # i, j, k, m, t, p, x_val
    viajes: pd.DataFrame        # i, j, m, t, p, n_val
    faltantes: pd.DataFrame     # j, k, t, p, f_val


def solve(
    model: gp.Model,
    mv: ModelVars,
    config: InstanceConfig,
    sets_obj: "Sets",  # type: ignore[name-defined]  # noqa: F821
) -> Solution:
    from core.sets import Sets
    s: Sets = sets_obj

    model.setParam("TimeLimit", config.time_limit_s)
    model.setParam("MIPGap", config.mip_gap)
    model.optimize()

    status_code = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }
    status = status_map.get(status_code, f"STATUS_{status_code}")

    if status_code == gp.GRB.INF_OR_UNBD:
        model.setParam("DualReductions", 0)
        model.optimize()
        status_code = model.Status
        status = status_map.get(status_code, f"STATUS_{status_code}")

    if status_code == gp.GRB.INFEASIBLE:
        iis_path = str(config.results_dir / "encontrar_infactibilidad.ilp")
        config.results_dir.mkdir(exist_ok=True)
        model.computeIIS()
        model.write(iis_path)
        raise RuntimeError(
            f"Model is INFEASIBLE. IIS written to {iis_path}. "
            "Check budget (R13), feasibility of demand coverage, "
            "or T^max constraints."
        )

    if status_code not in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT):
        raise RuntimeError(f"Unexpected solver status: {status}")

    obj = model.ObjVal
    gap = model.MIPGap if status_code == gp.GRB.TIME_LIMIT else 0.0
    runtime = model.Runtime

    # ── Extract solution ────────────────────────────────────────────────────
    rows_bod: list[dict[str, object]] = []
    for i in s.I:
        for t in s.T:
            rows_bod.append({
                "i": i, "t": t,
                "y": round(mv.y[i, t].X),
                "w": round(mv.w[i, t].X),
                "e": round(mv.e[i, t].X),
            })
    bodegas = pd.DataFrame(rows_bod)

    rows_inv: list[dict[str, object]] = []
    for i in s.I:
        for k in s.K:
            for t in s.T:
                s_val = mv.s[i, k, t].X
                c_val = mv.c[i, k, t].X
                if s_val > 1e-6 or c_val > 1e-6:
                    rows_inv.append({"i": i, "k": k, "t": t, "s": s_val, "c": c_val})
    inventario = pd.DataFrame(rows_inv)

    rows_env: list[dict[str, object]] = []
    for (i, j, k, m, t, p) in s.flow_keys:
        x_val = mv.x[i, j, k, m, t, p].X
        if x_val > 1e-6:
            rows_env.append({"i": i, "j": j, "k": k, "m": m, "t": t, "p": p, "x": x_val})
    envios = pd.DataFrame(rows_env)

    rows_viaj: list[dict[str, object]] = []
    for (i, j, m, t, p) in s.trip_keys:
        n_val = mv.n[i, j, m, t, p].X
        if n_val > 1e-6:
            rows_viaj.append({"i": i, "j": j, "m": m, "t": t, "p": p, "n": n_val})
    viajes = pd.DataFrame(rows_viaj)

    rows_falt: list[dict[str, object]] = []
    for (j, k, t, p) in s.short_keys:
        f_val = mv.f[j, k, t, p].X
        if f_val > 1e-6:
            rows_falt.append({"j": j, "k": k, "t": t, "p": p, "f": f_val})
    faltantes = pd.DataFrame(rows_falt)

    return Solution(
        obj_value=obj,
        gap=gap,
        runtime=runtime,
        status=status,
        bodegas=bodegas,
        inventario=inventario,
        envios=envios,
        viajes=viajes,
        faltantes=faltantes,
    )
