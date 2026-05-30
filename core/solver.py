from __future__ import annotations

from dataclasses import dataclass

import gurobipy as gp
import pandas as pd

from core.config import InstanceConfig
from core.parameters import Parameters
from core.sets import Sets
from core.variables import ModelVars


@dataclass
class Solution:
    obj_value: float
    gap: float
    runtime: float
    status: str
    # 6 reportes CSV
    bodegas_abiertas: pd.DataFrame   # i, t_apertura, costo_fijo, dotacion
    faltante: pd.DataFrame           # j, k, t, p, faltante
    inventario: pd.DataFrame         # i, k, t, stock_final, compras
    presupuesto: pd.DataFrame        # categoria, gasto_CLP
    personal: pd.DataFrame           # i, t, dotacion, saturacion_%
    rutas: pd.DataFrame              # i, j, m, t, p, viajes, volumen_m3, fill_rate_%


def solve(
    model: gp.Model,
    mv: ModelVars,
    config: InstanceConfig,
    sets: Sets,
    params: Parameters,
) -> Solution:
    p_obj = params

    model.setParam("TimeLimit", config.time_limit_s)
    model.setParam("MIPGap", config.mip_gap)
    model.optimize()

    status_code = model.Status
    STATUS_MAP = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }
    status = STATUS_MAP.get(status_code, f"STATUS_{status_code}")

    if status_code == gp.GRB.INF_OR_UNBD:
        model.setParam("DualReductions", 0)
        model.optimize()
        status_code = model.Status
        status = STATUS_MAP.get(status_code, f"STATUS_{status_code}")

    if status_code == gp.GRB.INFEASIBLE:
        config.results_dir.mkdir(exist_ok=True)
        iis_path = str(config.results_dir / "infactibilidad.ilp")
        model.computeIIS()
        model.write(iis_path)
        raise RuntimeError(
            f"INFEASIBLE. IIS en {iis_path}. "
            "Revisar: presupuesto R13, capacidad de bodega R4, o T^max."
        )

    if status_code not in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT):
        raise RuntimeError(f"Estado inesperado del solver: {status}")

    obj = model.ObjVal
    gap = model.MIPGap if status_code == gp.GRB.TIME_LIMIT else 0.0
    runtime = model.Runtime

    I, _, K, _, T, _ = sets.I, sets.J, sets.K, sets.M, sets.T, sets.P
    F = p_obj.F.to_dict()
    A = p_obj.A.to_dict()
    E_v = p_obj.E_vol.to_dict()
    V_k = p_obj.V.to_dict()
    H_k = p_obj.H.to_dict()
    Gm = p_obj.G_cost.to_dict()
    ab = {k: float(p_obj.alpha[k]) + float(p_obj.beta[k]) for k in K}
    rho = p_obj.rho
    d_h = p_obj.d

    # ── Reporte 1: Bodegas abiertas ────────────────────────────────────────
    rows_b: list[dict[str, object]] = []
    for i in I:
        for t in T:
            if mv.w[i, t].X > 0.5:
                rows_b.append({
                    "Bodega": i, "Mes_Apertura": t,
                    "Costo_Fijo_CLP": F[i],
                    "Dotacion_Mes_Apertura": round(mv.e[i, t].X),
                })
    bodegas_abiertas = pd.DataFrame(rows_b)

    # ── Reporte 2: Faltante ────────────────────────────────────────────────
    rows_f: list[dict[str, object]] = []
    for (j, k, t, p) in sets.short_keys:
        val = mv.f[j, k, t, p].X
        if val > 0.1:
            rows_f.append({"Comuna": j, "Insumo": k, "Mes": t,
                          "Prioridad": p, "Faltante": round(val, 1)})
    faltante = pd.DataFrame(rows_f)

    # ── Reporte 3: Inventario ──────────────────────────────────────────────
    rows_inv: list[dict[str, object]] = []
    for i in I:
        for k in K:
            for t in T:
                s_val = mv.s[i, k, t].X
                c_val = mv.c[i, k, t].X
                if s_val > 0.1 or c_val > 0.1:
                    rows_inv.append({"Bodega": i, "Insumo": k, "Mes": t, "Stock_Final": round(
                        s_val, 1), "Compras": round(c_val, 1)})
    inventario = pd.DataFrame(rows_inv)

    # ── Reporte 4: Presupuesto ─────────────────────────────────────────────
    g_ape = sum(F[i] * mv.w[i, t].X for i in I for t in T)
    g_com = sum(V_k[k] * mv.c[i, k, t].X for i in I for k in K for t in T)
    g_bod = sum(H_k[k] * mv.s[i, k, t].X for i in I for k in K for t in T)
    g_per = sum(p_obj.sueldo_mensual * mv.e[i, t].X for i in I for t in T)
    g_tra = sum(Gm[(i, j, m)] * mv.n[i, j, m, t,
                p].X for (i, j, m, t, p) in sets.trip_keys)
    presupuesto = pd.DataFrame({
        "Categoria": ["Apertura", "Compras", "Bodegaje", "Sueldos", "Transporte"],
        "Gasto_CLP": [g_ape, g_com, g_bod, g_per, g_tra],
    })

    # ── Reporte 5: Personal / saturación ──────────────────────────────────
    rows_per: list[dict[str, object]] = []
    for i in I:
        for t in T:
            dot = mv.e[i, t].X
            if dot > 0.5:
                min_usados = sum(
                    ab[k] * mv.x[i, j, k, m, t2, p].X
                    for (i2, j, k, m, t2, p) in sets.flow_keys
                    if i2 == i and t2 == t and mv.x[i2, j, k, m, t2, p].X > 0.5
                )
                min_max = dot * 60.0 * d_h * rho
                sat = (min_usados / min_max * 100) if min_max > 0 else 0.0
                rows_per.append({"Bodega": i, "Mes": t, "Dotacion": round(
                    dot), "Saturacion_%": round(sat, 1)})
    personal = pd.DataFrame(rows_per)

    # ── Reporte 6: Rutas / tasa de llenado ────────────────────────────────
    rows_r: list[dict[str, object]] = []
    for (i, j, m, t, p) in sets.trip_keys:
        viajes = mv.n[i, j, m, t, p].X
        if viajes > 0.5:
            vol = sum(
                E_v[k] * mv.x[i, j, k, m, t, p].X
                for k in K if (i, j, k, m, t, p) in mv.x
            )
            cap_total = A[m] * viajes
            fill = (vol / cap_total * 100) if cap_total > 0 else 0.0
            rows_r.append({
                "Origen": i, "Destino": j, "Vehiculo": m, "Mes": t, "Prioridad": p,
                "Viajes": int(round(viajes)),
                "Volumen_m3": round(vol, 2),
                "Fill_Rate_%": round(fill, 1),
            })
    rutas = pd.DataFrame(rows_r)

    return Solution(
        obj_value=obj, gap=gap, runtime=runtime, status=status,
        bodegas_abiertas=bodegas_abiertas,
        faltante=faltante,
        inventario=inventario,
        presupuesto=presupuesto,
        personal=personal,
        rutas=rutas,
    )
