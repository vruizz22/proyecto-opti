"""
pytest — verifica factibilidad, balances y consistencia del modelo.
Run: pytest test/test_model.py -v
"""
from __future__ import annotations
from core.config import InstanceConfig
from core.data_loader import load
from core.model_builder import build_model
from core.sets import build as build_sets

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.solver import solve
from scripts.generate_data import generate


@pytest.fixture(scope="module")
def solved():
    cfg = InstanceConfig()
    cfg.results_dir.mkdir(exist_ok=True)
    generate(cfg)
    params = load(cfg)
    sets = build_sets(cfg, params)
    model, mv = build_model(sets, params, cfg)
    sol = solve(model, mv, cfg, sets, params)
    return model, mv, sol, sets, params, cfg


def test_feasible(solved):
    _, _, sol, *_ = solved
    assert sol.status in ("OPTIMAL", "TIME_LIMIT"), f"Status: {sol.status}"


def test_demand_coverage_R1(solved):
    _, mv, _, sets, params, _ = solved
    D = params.D.to_dict()
    for (j, k, t, p) in sets.short_keys:
        dem = D.get((j, k, t, p), 0.0)
        cov = sum(
            mv.x[i, j, k, m, t, p].X
            for i in sets.I for m in sets.M
            if (i, j, k, m, t, p) in mv.x
        )
        short = mv.f[j, k, t, p].X
        assert cov + short >= dem - 1e-3, (
            f"R1 violada: ({j},{k},{t},{p}) cov={cov:.2f} f={short:.2f} D={dem:.2f}"
        )


def test_perishable_stock_zero_R3(solved):
    _, mv, _, sets, *_ = solved
    for i in sets.I:
        for k in sets.Kv:
            for t in sets.T:
                val = mv.s[i, k, t].X
                assert val < 1e-4, f"R3 violada: s[{i},{k},{t}]={val:.4f}"


def test_inventory_balance_R2(solved):
    _, mv, _, sets, params, _ = solved
    S0 = params.S0.to_dict()
    for i in sets.I:
        for k in sets.Kn:
            for t in sets.T:
                s_prev = S0.get((i, k), 0.0) if t == 1 else mv.s[i, k, t - 1].X
                out = sum(
                    mv.x[i, j, k, m, t, p].X
                    for j in sets.J for m in sets.M for p in sets.P
                    if (i, j, k, m, t, p) in mv.x
                )
                lhs = mv.s[i, k, t].X
                rhs = s_prev + mv.c[i, k, t].X - out
                assert abs(lhs - rhs) < 1e-2, (
                    f"R2 violada: ({i},{k},{t}) s={lhs:.3f} rhs={rhs:.3f}"
                )


def test_budget_R13(solved):
    _, mv, _, sets, params, _ = solved
    F = params.F.to_dict()
    V = params.V.to_dict()
    H = params.H.to_dict()
    G = params.G_cost.to_dict()
    omega = params.sueldo_mensual
    total = 0.0
    for i in sets.I:
        for t in sets.T:
            total += F[i] * mv.w[i, t].X
            total += omega * mv.e[i, t].X
            for k in sets.K:
                total += V[k] * mv.c[i, k, t].X
                total += H[k] * mv.s[i, k, t].X
    for (i, j, m, t, p) in sets.trip_keys:
        total += G[(i, j, m)] * mv.n[i, j, m, t, p].X
    assert total <= params.B + \
        1.0, f"R13 violada: costo={total:.0f} > B={params.B:.0f}"


def test_vehicle_capacity_R5(solved):
    _, mv, _, sets, params, _ = solved
    A = params.A.to_dict()
    E = params.E_vol.to_dict()
    for (i, j, m, t, p) in sets.trip_keys:
        vol = sum(
            E[k] * mv.x[i, j, k, m, t, p].X
            for k in sets.K if (i, j, k, m, t, p) in mv.x
        )
        trips = mv.n[i, j, m, t, p].X
        assert vol <= A[m] * trips + 1e-3, (
            f"R5 violada: ({i},{j},{m},{t},{p}) vol={vol:.3f} > A*n={A[m] * trips:.3f}"
        )
