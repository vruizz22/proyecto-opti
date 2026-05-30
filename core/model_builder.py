"""
Build Gurobi model with all R1–R14 constraints exactly as in main.tex.
Structural sparsity: x and n only exist for feasible (Apt=1, T+O<=T^max_p, D>0) tuples.
R8 and zero-n part of R6 are enforced by variable non-existence (no constraint needed).
"""
from __future__ import annotations

import gurobipy as gp
from gurobipy import quicksum

from core.config import InstanceConfig
from core.parameters import Parameters
from core.sets import Sets
from core.variables import ModelVars, create_vars


def build_model(
    sets: Sets,
    params: Parameters,
    config: InstanceConfig,
) -> tuple[gp.Model, ModelVars]:
    model = gp.Model("SENAPRED_logistics")
    model.setParam("OutputFlag", 1)

    mv = create_vars(model, sets)
    w, y, s, c, x, n, e, f = mv.w, mv.y, mv.s, mv.c, mv.x, mv.n, mv.e, mv.f

    I, J, K, M, T, P = sets.I, sets.J, sets.K, sets.M, sets.T, sets.P
    Kv, Kn = sets.Kv, sets.Kn
    T_dem = sets.T_dem
    Ig = sets.Ig

    # Parameter lookups (dicts for O(1) access inside quicksum)
    D = params.D.to_dict()
    C = params.C.to_dict()
    E_vol = params.E_vol.to_dict()
    F = params.F.to_dict()
    V = params.V.to_dict()
    H = params.H.to_dict()
    A = params.A.to_dict()
    T_travel = params.T_travel.to_dict()
    O = params.O.to_dict()
    G_cost = params.G_cost.to_dict()
    W = params.W.to_dict()
    S0 = params.S0.to_dict()
    alpha = params.alpha.to_dict()
    beta = params.beta.to_dict()
    L = params.L.to_dict()
    Emax_p = params.Emax.to_dict()
    Omega = params.Omega.to_dict()
    Q = params.Q.to_dict()
    pi = params.pi.to_dict()
    rho = params.rho
    d_hours = params.d
    h = params.h

    k_to_p = config.priority_of_supply

    # ── Objective ──────────────────────────────────────────────────────────────
    # Term 1: W_p * (T_{ijrmt} + O_m) * n_{ijrmtp}
    obj_travel = quicksum(
        W[p] * (T_travel[(i, j, m, t)] + O[m]) * n[i, j, m, t, p]
        for (i, j, m, t, p) in sets.trip_keys
    )
    # Term 2: W_p * (alpha_k + beta_k) * x_{ijkmtp}
    obj_manip = quicksum(
        W[p] * (alpha[k] + beta[k]) * x[i, j, k, m, t, p]
        for (i, j, k, m, t, p) in sets.flow_keys
    )
    # Term 3: h * G_{ijm} * n_{ijmtp}
    obj_cost = quicksum(
        h * G_cost[(i, j, m)] * n[i, j, m, t, p]
        for (i, j, m, t, p) in sets.trip_keys
    )
    # Term 4: pi_p * f_{jktp}
    obj_short = quicksum(pi[p] * f[j, k, t, p] for (j, k, t, p) in sets.short_keys)

    model.setObjective(obj_travel + obj_manip + obj_cost + obj_short, gp.GRB.MINIMIZE)

    # ── R1: Satisfacción de demanda con holgura ─────────────────────────────
    for (j, k, t, p) in sets.short_keys:
        model.addConstr(
            quicksum(
                x[i, j, k, m, t, p]
                for i in I
                for m in M
                if (i, j, k, m, t, p) in x
            )
            + f[j, k, t, p]
            >= D.get((j, k, t, p), 0.0),
            name=f"R1_j{j}_k{k}_t{t}_p{p}",
        )

    # ── R2: Balance inventario no perecibles ────────────────────────────────
    for i in I:
        for k in Kn:
            for t in T:
                s_prev = S0.get((i, k), 0.0) if t == 1 else s[i, k, t - 1]
                outflow = quicksum(
                    x[i, j, k, m, t, p]
                    for j in J
                    for m in M
                    for p in P
                    if (i, j, k, m, t, p) in x
                )
                model.addConstr(
                    s[i, k, t] == s_prev + c[i, k, t] - outflow,
                    name=f"R2_i{i}_k{k}_t{t}",
                )

    # ── R3: No acumulación perecibles ───────────────────────────────────────
    for i in I:
        for k in Kv:
            for t in T:
                outflow = quicksum(
                    x[i, j, k, m, t, p]
                    for j in J
                    for m in M
                    for p in P
                    if (i, j, k, m, t, p) in x
                )
                model.addConstr(
                    c[i, k, t] == outflow,
                    name=f"R3_i{i}_k{k}_t{t}",
                )
                # s=0 for perishables (implied by R3 + s>=0, but explicit for clarity)
                model.addConstr(s[i, k, t] == 0.0, name=f"R3s_i{i}_k{k}_t{t}")

    # ── R4: Capacidad física de bodega ──────────────────────────────────────
    for i in I:
        for t in T:
            model.addConstr(
                quicksum(E_vol[k] * s[i, k, t] for k in K) <= C[i] * y[i, t],
                name=f"R4_i{i}_t{t}",
            )

    # ── R5: Capacidad de transporte por ruta ────────────────────────────────
    for (i, j, m, t, p) in sets.trip_keys:
        model.addConstr(
            quicksum(
                E_vol[k] * x[i, j, k, m, t, p]
                for k in K
                if (i, j, k, m, t, p) in x
            )
            <= A[m] * n[i, j, m, t, p],
            name=f"R5_i{i}_j{j}_m{m}_t{t}_p{p}",
        )

    # ── R6: Viajes condicionados a apertura (big-M tight = Q_{mt}) ──────────
    # n_{ijrmtp}=0 if not in F_p is structural (variable doesn't exist outside trip_keys)
    for (i, j, m, t, p) in sets.trip_keys:
        big_m = Q.get((m, t), 0)
        model.addConstr(
            n[i, j, m, t, p] <= big_m * y[i, t],
            name=f"R6_i{i}_j{j}_m{m}_t{t}_p{p}",
        )

    # ── R7: Disponibilidad institucional de flota ───────────────────────────
    for m in M:
        for t in T_dem:
            model.addConstr(
                quicksum(
                    n[i, j, m, t, p]
                    for i in I
                    for j in J
                    for p in P
                    if (i, j, m, t, p) in n
                )
                <= Q.get((m, t), 0),
                name=f"R7_m{m}_t{t}",
            )

    # ── R8: implícita — variables n/x solo existen donde Apt=1 ──────────────

    # ── R9: Capacidad operativa cuadrillas ──────────────────────────────────
    for i in I:
        for t in T:
            model.addConstr(
                quicksum(
                    (alpha[k] + beta[k]) * x[i, j, k, m, t, p]
                    for j in J
                    for k in K
                    for m in M
                    for p in P
                    if (i, j, k, m, t, p) in x
                )
                <= e[i, t] * 60.0 * d_hours * rho,
                name=f"R9_i{i}_t{t}",
            )

    # ── R10a: Piso dotación mínima ──────────────────────────────────────────
    for i in I:
        g = Ig[i]
        for t in T:
            model.addConstr(
                L[g] * y[i, t] <= e[i, t],
                name=f"R10a_i{i}_t{t}",
            )

    # ── R10b: Techo dotación máxima ─────────────────────────────────────────
    for i in I:
        g = Ig[i]
        for t in T:
            model.addConstr(
                e[i, t] <= Emax_p[g] * y[i, t],
                name=f"R10b_i{i}_t{t}",
            )

    # ── R11: Capacidad de salida multiruta ──────────────────────────────────
    for i in I:
        for k in K:
            for t in T:
                s_prev = S0.get((i, k), 0.0) if t == 1 else s[i, k, t - 1]
                model.addConstr(
                    quicksum(
                        x[i, j, k, m, t, p]
                        for j in J
                        for m in M
                        for p in P
                        if (i, j, k, m, t, p) in x
                    )
                    <= s_prev + c[i, k, t],
                    name=f"R11_i{i}_k{k}_t{t}",
                )

    # ── R12a: Apertura única estratégica ────────────────────────────────────
    for i in I:
        model.addConstr(
            quicksum(w[i, t] for t in T) <= 1,
            name=f"R12a_i{i}",
        )

    # ── R12b: Operación continua heredada (y_{i,0}=0) ───────────────────────
    for i in I:
        for t in T:
            y_prev = 0 if t == 1 else y[i, t - 1]
            model.addConstr(y[i, t] >= y_prev, name=f"R12b_i{i}_t{t}")

    # ── R12c: Activación en período de apertura ─────────────────────────────
    for i in I:
        for t in T:
            model.addConstr(y[i, t] >= w[i, t], name=f"R12c_i{i}_t{t}")

    # ── R13: Presupuesto total ───────────────────────────────────────────────
    cost_open = quicksum(F[i] * w[i, t] for i in I for t in T)
    cost_buy = quicksum(V[(k, t)] * c[i, k, t] for i in I for k in K for t in T)
    cost_hold = quicksum(H[(i, k, t)] * s[i, k, t] for i in I for k in K for t in T)
    cost_staff = quicksum(Omega[t] * e[i, t] for i in I for t in T)
    cost_routes = quicksum(
        G_cost[(i, j, m)] * n[i, j, m, t, p]
        for (i, j, m, t, p) in sets.trip_keys
    )
    model.addConstr(
        cost_open + cost_buy + cost_hold + cost_staff + cost_routes <= params.B,
        name="R13_budget",
    )

    # ── R14: Compras condicionadas a apertura (tight big-M) ─────────────────
    for i in I:
        for k in K:
            for t in T:
                # tight M: C_i / min(E_k)
                e_min = min(E_vol.values())
                big_m14 = C[i] / e_min
                model.addConstr(
                    c[i, k, t] <= big_m14 * y[i, t],
                    name=f"R14_i{i}_k{k}_t{t}",
                )

    model.update()
    return model, mv
