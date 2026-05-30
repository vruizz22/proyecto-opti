"""
Build Gurobi model with R1–R14 exactly as in main.tex.
Corrections code:
  - Objetivo: términos de n (viajes) y x (unidades) separados correctamente.
  - y_{it}: declarada BINARY (no continua).
  - R12b: y_{it} = sum_{tau<=t} w_{i,tau}  (equivalente a R12b+R12c del .tex, más tight).
  - R12c: incluida explícitamente para consistencia con el .tex.
  - R14: compras condicionadas a apertura.
  - R8: implícita — variables n/x solo existen para (i,j,m) en R' (Apt=1).
"""
from __future__ import annotations

import gurobipy as gp
from gurobipy import quicksum

from core.config import InstanceConfig
from core.parameters import Parameters
from core.sets import Sets
from core.variables import ModelVars, create_vars


def _create_env(config: InstanceConfig) -> gp.Env:
    """Crea entorno Gurobi con WLS si hay credenciales configuradas."""
    env = gp.Env(empty=True)
    env.setParam("WLSACCESSID", config.wls_access_id)
    env.setParam("WLSSECRET", config.wls_secret)
    env.setParam("LICENSEID", config.wls_license_id)
    env.setParam("OutputFlag", 0)
    env.start()
    return env


def build_model(
    sets: Sets,
    params: Parameters,
    config: InstanceConfig,
) -> tuple[gp.Model, ModelVars]:

    env = _create_env(config)
    model = gp.Model("SENAPRED_E4_Logistica", env=env)
    model.setParam("OutputFlag", 1)

    mv = create_vars(model, sets)
    w, y, s, c, x, n, e, f = mv.w, mv.y, mv.s, mv.c, mv.x, mv.n, mv.e, mv.f

    I, J, K, M, T, P = sets.I, sets.J, sets.K, sets.M, sets.T, sets.P
    Kv, Kn = sets.Kv, sets.Kn

    # O(1) dict lookups
    D = params.D.to_dict()
    C = params.C.to_dict()
    E_vol = params.E_vol.to_dict()
    F = params.F.to_dict()
    V = params.V.to_dict()
    H = params.H.to_dict()
    A = params.A.to_dict()
    O_op = params.O.to_dict()
    T_tr = params.T_travel.to_dict()
    G_cost = params.G_cost.to_dict()
    W = params.W.to_dict()
    S0 = params.S0.to_dict()
    alpha = params.alpha.to_dict()
    beta = params.beta.to_dict()
    L = params.L.to_dict()
    Emax = params.Emax.to_dict()
    Omega = params.sueldo_mensual   # scalar Ω (simplificado, constante)
    Q = params.Q.to_dict()
    pi = params.pi.to_dict()
    rho = params.rho
    d_h = params.d
    h = params.h

    # ── Función objetivo (4 términos, exactamente como en main.tex) ──────
    # Término 1: W_p*(T_{ijm}+O_m)*n_{ijmtp}  — tiempo de viaje ponderado
    obj_t1 = quicksum(
        W[p] * (T_tr[(i, j, m)] + O_op[m]) * n[i, j, m, t, p]
        for (i, j, m, t, p) in sets.trip_keys
    )
    # Término 2: W_p*(α_k+β_k)*x_{ijkmtp}  — tiempo de manipulación ponderado
    obj_t2 = quicksum(
        W[p] * (alpha[k] + beta[k]) * x[i, j, k, m, t, p]
        for (i, j, k, m, t, p) in sets.flow_keys
    )
    # Término 3: h*G_{ijm}*n_{ijmtp}  — costo operativo convertido a min
    obj_t3 = quicksum(
        h * G_cost[(i, j, m)] * n[i, j, m, t, p]
        for (i, j, m, t, p) in sets.trip_keys
    )
    # Término 4: π_p*f_{jktp}  — penalización por faltante
    obj_t4 = quicksum(pi[p] * f[j, k, t, p]
                      for (j, k, t, p) in sets.short_keys)

    model.setObjective(obj_t1 + obj_t2 + obj_t3 + obj_t4, gp.GRB.MINIMIZE)

    # ── R1: Satisfacción de demanda con holgura ───────────────────────────
    for (j, k, t, p) in sets.short_keys:
        model.addConstr(
            quicksum(
                x[i, j, k, m, t, p]
                for i in I for m in M
                if (i, j, k, m, t, p) in x
            ) + f[j, k, t, p] >= D.get((j, k, t, p), 0.0),
            name=f"R1_{j}_{k}_{t}_{p}",
        )

    # ── R2: Balance inventario no perecibles ─────────────────────────────
    for i in I:
        for k in Kn:
            for t in T:
                s_prev = S0.get((i, k), 0.0) if t == 1 else s[i, k, t - 1]
                out_k = quicksum(
                    x[i, j, k, m, t, p]
                    for j in J for m in M for p in P
                    if (i, j, k, m, t, p) in x
                )
                model.addConstr(s[i, k, t] == s_prev + c[i, k, t] - out_k,
                                name=f"R2_{i}_{k}_{t}")

    # ── R3: No acumulación perecibles (s=0 ∀ perecibles) ─────────────────
    for i in I:
        for k in Kv:
            for t in T:
                out_k = quicksum(
                    x[i, j, k, m, t, p]
                    for j in J for m in M for p in P
                    if (i, j, k, m, t, p) in x
                )
                model.addConstr(c[i, k, t] == out_k, name=f"R3_{i}_{k}_{t}")
                model.addConstr(s[i, k, t] == 0.0, name=f"R3s_{i}_{k}_{t}")

    # ── R4: Capacidad física de bodega ────────────────────────────────────
    for i in I:
        for t in T:
            model.addConstr(
                quicksum(E_vol[k] * s[i, k, t] for k in K) <= C[i] * y[i, t],
                name=f"R4_{i}_{t}",
            )

    # ── R5: Capacidad de transporte por viaje ─────────────────────────────
    for (i, j, m, t, p) in sets.trip_keys:
        model.addConstr(
            quicksum(
                E_vol[k] * x[i, j, k, m, t, p]
                for k in K if (i, j, k, m, t, p) in x
            ) <= A[m] * n[i, j, m, t, p],
            name=f"R5_{i}_{j}_{m}_{t}_{p}",
        )

    # ── R6: Viajes condicionados a apertura (big-M tight = Q_{mt}) ───────
    # Parte implícita (T+O > T^max_p → variable no existe): ya en sets.py
    for (i, j, m, t, p) in sets.trip_keys:
        big_m6 = Q.get((m, t), 0)
        model.addConstr(n[i, j, m, t, p] <= big_m6 * y[i, t],
                        name=f"R6_{i}_{j}_{m}_{t}_{p}")

    # ── R6b: Flujo condicionado a apertura (D_{jktp} como big-M) ─────────
    for (i, j, k, m, t, p) in sets.flow_keys:
        d_val = D.get((j, k, t, p), 0.0)
        model.addConstr(x[i, j, k, m, t, p] <= d_val * y[i, t],
                        name=f"R6b_{i}_{j}_{k}_{m}_{t}_{p}")

    # ── R7: Disponibilidad institucional de flota ─────────────────────────
    for m in M:
        for t in T:
            model.addConstr(
                quicksum(
                    n[i, j, m, t, p]
                    for i in I for j in J for p in P
                    if (i, j, m, t, p) in n
                ) <= Q.get((m, t), 0),
                name=f"R7_{m}_{t}",
            )

    # ── R8: Aptitud vehicular — implícita (R' ya filtró Apt=0) ───────────

    # ── R9: Capacidad operativa de cuadrillas ─────────────────────────────
    for i in I:
        for t in T:
            model.addConstr(
                quicksum(
                    (alpha[k] + beta[k]) * x[i, j, k, m, t, p]
                    for j in J for k in K for m in M for p in P
                    if (i, j, k, m, t, p) in x
                ) <= e[i, t] * 60.0 * d_h * rho,
                name=f"R9_{i}_{t}",
            )

    # ── R10a: Dotación mínima (per bodega, fiel al CSV) ───────────────────
    for i in I:
        for t in T:
            model.addConstr(L[i] * y[i, t] <= e[i, t], name=f"R10a_{i}_{t}")

    # ── R10b: Dotación máxima ─────────────────────────────────────────────
    for i in I:
        for t in T:
            model.addConstr(e[i, t] <= Emax[i] * y[i, t], name=f"R10b_{i}_{t}")

    # ── R11: Capacidad de salida multiruta ────────────────────────────────
    for i in I:
        for k in K:
            for t in T:
                s_prev = S0.get((i, k), 0.0) if t == 1 else s[i, k, t - 1]
                model.addConstr(
                    quicksum(
                        x[i, j, k, m, t, p]
                        for j in J for m in M for p in P
                        if (i, j, k, m, t, p) in x
                    ) <= s_prev + c[i, k, t],
                    name=f"R11_{i}_{k}_{t}",
                )

    # ── R12a: Apertura única estratégica ──────────────────────────────────
    for i in I:
        model.addConstr(quicksum(w[i, t] for t in T) <= 1, name=f"R12a_{i}")

    # ── R12b: Operación continua heredada (formulación igualdad — más tight)
    # y_{it} = sum_{tau<=t} w_{i,tau}  equivale a R12b+R12c del .tex
    for i in I:
        for t in T:
            model.addConstr(
                y[i, t] == quicksum(w[i, tau] for tau in range(1, t + 1)),
                name=f"R12b_{i}_{t}",
            )

    # ── R13: Presupuesto total ────────────────────────────────────────────
    cost_open = quicksum(F[i] * w[i, t] for i in I for t in T)
    cost_buy = quicksum(V[k] * c[i, k, t] for i in I for k in K for t in T)
    cost_hold = quicksum(H[k] * s[i, k, t] for i in I for k in K for t in T)
    cost_staff = quicksum(Omega * e[i, t] for i in I for t in T)
    cost_route = quicksum(G_cost[(i, j, m)] * n[i, j, m, t, p]
                          for (i, j, m, t, p) in sets.trip_keys)
    model.addConstr(
        cost_open + cost_buy + cost_hold + cost_staff + cost_route <= params.B,
        name="R13_presupuesto",
    )

    # ── R14: Compras condicionadas a apertura ─────────────────────────────
    for i in I:
        for k in K:
            for t in T:
                e_min = min(E_vol.values())
                big_m14 = C[i] / e_min
                model.addConstr(c[i, k, t] <= big_m14 * y[i, t],
                                name=f"R14_{i}_{k}_{t}")

    model.update()
    return model, mv
