"""
pytest suite: cap < 2000, feasibility, inventory balances.
Run: pytest test/test_model.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import InstanceConfig
from core.data_loader import load
from core.model_builder import build_model
from core.sets import build
from core.solver import solve
from scripts.generate_data import generate


@pytest.fixture(scope="module")
def solution():
    config = InstanceConfig()
    config.results_dir.mkdir(exist_ok=True)
    generate(config)
    params = load(config)
    sets = build(config, params)
    model, mv = build_model(sets, params, config)
    sol = solve(model, mv, config, sets)
    return model, mv, sol, sets, params, config


def test_var_cap(solution):
    model, *_ = solution
    assert model.NumVars < 2000, f"NumVars={model.NumVars} ≥ 2000"


def test_constr_cap(solution):
    model, *_ = solution
    assert model.NumConstrs < 2000, f"NumConstrs={model.NumConstrs} ≥ 2000"


def test_feasible(solution):
    _, _, sol, *_ = solution
    assert sol.status in ("OPTIMAL", "TIME_LIMIT"), f"Solver status: {sol.status}"


def test_demand_coverage_R1(solution):
    """For each (j,k,t,p) in short_keys: envios + faltante >= D."""
    _, mv, sol, sets, params, config = solution
    D = params.D.to_dict()
    for (j, k, t, p) in sets.short_keys:
        demand = D.get((j, k, t, p), 0.0)
        covered = sum(
            mv.x[i, jj, kk, m, tt, pp].X
            for (i, jj, kk, m, tt, pp) in sets.flow_keys
            if jj == j and kk == k and tt == t and pp == p
        )
        faltante = mv.f[j, k, t, p].X
        assert covered + faltante >= demand - 1e-4, (
            f"R1 violated: j={j} k={k} t={t} p={p} "
            f"covered={covered:.2f} f={faltante:.2f} D={demand:.2f}"
        )


def test_perishable_inventory_zero_R3(solution):
    """Perishable stock s_{ikt}=0 for all i,k in Kv,t."""
    _, mv, sol, sets, *_ = solution
    for i in sets.I:
        for k in sets.Kv:
            for t in sets.T:
                val = mv.s[i, k, t].X
                assert val < 1e-4, f"R3 violated: s[{i},{k},{t}]={val:.4f}"


def test_inventory_balance_R2(solution):
    """Non-perishable inventory balance holds (tolerance 1e-3)."""
    _, mv, sol, sets, params, config = solution
    S0 = params.S0.to_dict()
    for i in sets.I:
        for k in sets.Kn:
            for t in sets.T:
                s_prev = S0.get((i, k), 0.0) if t == 1 else mv.s[i, k, t - 1].X
                outflow = sum(
                    mv.x[i, j, k, m, t, p].X
                    for j in sets.J
                    for m in sets.M
                    for p in sets.P
                    if (i, j, k, m, t, p) in mv.x
                )
                lhs = mv.s[i, k, t].X
                rhs = s_prev + mv.c[i, k, t].X - outflow
                assert abs(lhs - rhs) < 1e-3, (
                    f"R2 violated: i={i} k={k} t={t} s={lhs:.4f} rhs={rhs:.4f}"
                )


def test_budget_R13(solution):
    """Total cost does not exceed budget B."""
    _, mv, sol, sets, params, config = solution
    F = params.F.to_dict()
    V = params.V.to_dict()
    H = params.H.to_dict()
    Omega = params.Omega.to_dict()
    G_cost = params.G_cost.to_dict()

    total = 0.0
    for i in sets.I:
        for t in sets.T:
            total += F[i] * mv.w[i, t].X
            total += Omega[t] * mv.e[i, t].X
            for k in sets.K:
                total += V[(k, t)] * mv.c[i, k, t].X
                total += H[(i, k, t)] * mv.s[i, k, t].X

    for (i, j, m, t, p) in sets.trip_keys:
        total += G_cost[(i, j, m)] * mv.n[i, j, m, t, p].X

    assert total <= params.B + 1.0, f"R13 violated: cost={total:.0f} > B={params.B:.0f}"
