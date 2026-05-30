"""
pytest — verifica factibilidad, restricciones y calidad de solución (E4).
Run:  pytest test/test_model.py -v

Bounds calibrated against E4 run:
  - 12/12 bodegas abiertas
  - P1 faltante = 296 u  (E3 legacy: 20,601 u)
  - GAP = 2.82%
  - Z* ≈ 161.5 MM min-equiv
"""
from __future__ import annotations

import sys
from pathlib import Path
# sys.path must be set before any local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import TYPE_CHECKING


import pytest  # type: ignore[import-untyped]

from core.config import InstanceConfig
from core.data_loader import load
from core.model_builder import build_model
from core.sets import build as build_sets
from core.solver import Solution, solve
from scripts.generate_data import generate

if TYPE_CHECKING:
    import gurobipy as gp
    from core.variables import ModelVars
    from core.sets import Sets
    from core.parameters import Parameters

# (model, mv, sol, sets, params, cfg)
type _Solved = tuple[gp.Model, ModelVars, Solution, Sets, Parameters, InstanceConfig]

_TOL = 1e-3   # tolerancia numérica para restricciones continuas
_TOL_BUDGET = 1.0  # CLP — slack por redondeo en restricción R13


_TEST_TIME_LIMIT: float = 120.0  # 2 min — suficiente para obtener incumbente


@pytest.fixture(scope="module")  # type: ignore[misc]
def solved() -> _Solved:
    cfg = InstanceConfig(time_limit_s=_TEST_TIME_LIMIT)
    cfg.results_dir.mkdir(exist_ok=True)
    generate(cfg)
    params = load(cfg)
    sets = build_sets(cfg, params)
    model, mv = build_model(sets, params, cfg)
    sol = solve(model, mv, cfg, sets, params)
    return model, mv, sol, sets, params, cfg


# ── Estado del solver ────────────────────────────────────────────────────────

def test_feasible(solved: _Solved) -> None:
    """El solver debe terminar en OPTIMAL o TIME_LIMIT con solución incumbente."""
    _, _, sol, *_ = solved
    assert sol.status in ("OPTIMAL", "TIME_LIMIT"), f"Estado inesperado: {sol.status}"
    assert sol.obj_value > 0, "Función objetivo debe ser positiva (min tiempo+penalización)"


def test_gap_acceptable(solved: _Solved) -> None:
    """GAP < 40 % con TimeLimit=120 s (run completo alcanza 2.82 % en 1800 s)."""
    _, _, sol, *_ = solved
    assert sol.gap < 0.40, f"GAP demasiado alto: {sol.gap:.4%}"


# ── Restricciones del modelo ─────────────────────────────────────────────────

def test_demand_coverage_R1(solved: _Solved) -> None:
    """R1: cobertura + faltante ≥ demanda en cada (j,k,t,p)."""
    _, mv, _, sets, params, _ = solved
    D = params.D.to_dict()
    for (j, k, t, p) in sets.short_keys:
        dem = D.get((j, k, t, p), 0.0)
        cov = sum(
            mv.x[i, j, k, m, t, p].X
            for i in sets.I
            for m in sets.M
            if (i, j, k, m, t, p) in mv.x
        )
        short = mv.f[j, k, t, p].X
        assert cov + short >= dem - _TOL, (
            f"R1 violada: ({j},{k},{t},{p})  cov={cov:.2f}  f={short:.2f}  D={dem:.2f}"
        )


def test_perishable_stock_zero_R3(solved: _Solved) -> None:
    """R3: stock de perecibles debe ser cero (se despachan en el mismo mes)."""
    _, mv, _, sets, *_ = solved
    for i in sets.I:
        for k in sets.Kv:
            for t in sets.T:
                val = mv.s[i, k, t].X
                assert val < _TOL, f"R3 violada: s[{i},{k},{t}]={val:.4f}"


def test_inventory_balance_R2(solved: _Solved) -> None:
    """R2: balance de inventario no perecible s[t] = s[t-1] + c[t] - salidas."""
    _, mv, _, sets, params, _ = solved
    S0 = params.S0.to_dict()
    for i in sets.I:
        for k in sets.Kn:
            for t in sets.T:
                s_prev = S0.get((i, k), 0.0) if t == 1 else mv.s[i, k, t - 1].X
                out = sum(
                    mv.x[i, j, k, m, t, p].X
                    for j in sets.J
                    for m in sets.M
                    for p in sets.P
                    if (i, j, k, m, t, p) in mv.x
                )
                lhs = mv.s[i, k, t].X
                rhs = s_prev + mv.c[i, k, t].X - out
                assert abs(lhs - rhs) < 1e-2, (
                    f"R2 violada: ({i},{k},{t})  s={lhs:.3f}  rhs={rhs:.3f}"
                )


def test_budget_R13(solved: _Solved) -> None:
    """R13: gasto total ≤ B (presupuesto global)."""
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
    assert total <= params.B + _TOL_BUDGET, (
        f"R13 violada: gasto={total:,.0f}  >  B={params.B:,.0f}"
    )


def test_vehicle_capacity_R5(solved: _Solved) -> None:
    """R5: volumen despachado ≤ capacidad × viajes para cada (i,j,m,t,p)."""
    _, mv, _, sets, params, _ = solved
    A = params.A.to_dict()
    E = params.E_vol.to_dict()
    for (i, j, m, t, p) in sets.trip_keys:
        vol = sum(
            E[k] * mv.x[i, j, k, m, t, p].X
            for k in sets.K
            if (i, j, k, m, t, p) in mv.x
        )
        trips = mv.n[i, j, m, t, p].X
        assert vol <= A[m] * trips + _TOL, (
            f"R5 violada: ({i},{j},{m},{t},{p})  vol={vol:.3f}  >  A*n={A[m]*trips:.3f}"
        )


# ── Calidad de la solución E4 ────────────────────────────────────────────────

def test_all_bodegas_open(solved: _Solved) -> None:
    """E4 abre las 12 bodegas desde el mes 1; si no, hay regresión en cobertura."""
    _, _, sol, sets, *_ = solved
    n_open = len(sol.bodegas_abiertas)
    assert n_open == len(sets.I), (
        f"Solo {n_open}/{len(sets.I)} bodegas abiertas — revisar restricciones de apertura"
    )


def test_p1_faltante_below_threshold(solved: _Solved) -> None:
    """Faltante P1 < 5.000 u con 120 s de solver (run completo: 296 u en 1800 s)."""
    _, _, sol, *_ = solved
    p1 = sol.faltante[sol.faltante["Prioridad"] == 1]["Faltante"].sum()
    assert p1 < 5_000, f"P1 faltante={p1:.0f} u supera umbral — regresión en triage"


def test_triage_priority_ordering(solved: _Solved) -> None:
    """Triage: faltante P3 >> P2 >> P1 (el modelo sacrifica baja prioridad)."""
    _, _, sol, *_ = solved
    f = sol.faltante.groupby("Prioridad")["Faltante"].sum()
    p1 = float(f.get(1, 0.0))
    p2 = float(f.get(2, 0.0))
    p3 = float(f.get(3, 0.0))
    assert p3 > p2 > p1, (
        f"Orden de triage incorrecto: P1={p1:.0f}  P2={p2:.0f}  P3={p3:.0f}"
    )


def test_bodegaje_cost_positive(solved: _Solved) -> None:
    """R14/R9: si hay stock no perecible > 0 debe haber costo de mantención > 0."""
    _, _, sol, *_ = solved
    bodegaje_row = sol.presupuesto[sol.presupuesto["Categoria"] == "Bodegaje"]
    assert not bodegaje_row.empty, "Categoría 'Bodegaje' ausente en reporte de presupuesto"
    bodegaje = float(bodegaje_row["Gasto_CLP"].iloc[0])
    assert bodegaje > 0, (
        "Gasto de bodegaje = 0 — posible error en R9 (costo mantención no contabilizado)"
    )


def test_solution_reports_complete(solved: _Solved) -> None:
    """Solution.bodegas_abiertas, faltante, inventario, presupuesto, personal, rutas no vacíos."""
    _, _, sol, *_ = solved
    assert len(sol.bodegas_abiertas) > 0
    assert len(sol.faltante) > 0
    assert len(sol.inventario) > 0
    assert len(sol.presupuesto) > 0
    assert len(sol.personal) > 0
    assert len(sol.rutas) > 0
