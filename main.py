"""
SENAPRED Humanitarian Logistics Optimization — E3
Run: python main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root on path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from core.config import InstanceConfig
from core.data_loader import load
from core.model_builder import build_model
from core.sets import build
from core.solver import solve
from scripts.generate_data import generate
from views.plots import generate_plots
from views.results_writer import write_results


def main() -> None:
    config = InstanceConfig()
    config.results_dir.mkdir(exist_ok=True)

    # Step 1: generate data if missing
    if not (config.data_dir / "demanda.csv").exists():
        print("[main] Generating synthetic data...")
        generate(config)

    # Step 2: load parameters
    print("[main] Loading parameters...")
    params = load(config)

    # Step 3: build sets (sparsity)
    print("[main] Building sets...")
    sets = build(config, params)

    # Step 4: build model
    print("[main] Building model...")
    model, mv = build_model(sets, params, config)

    n_vars = model.NumVars
    n_constrs = model.NumConstrs
    print(f"[main] NumVars={n_vars}  NumConstrs={n_constrs}")

    if n_vars >= 2000 or n_constrs >= 2000:
        print(
            f"[main] ERROR: License cap exceeded! "
            f"NumVars={n_vars}, NumConstrs={n_constrs}. "
            "Reduce T_dem in InstanceConfig (e.g. fire_months=(1,2)) and re-run."
        )
        sys.exit(1)

    # Step 5: solve
    print("[main] Solving...")
    sol = solve(model, mv, config, sets)

    print(f"\n[main] Status={sol.status}  Obj={sol.obj_value:,.0f}  "
          f"GAP={sol.gap*100:.2f}%  Runtime={sol.runtime:.1f}s")

    # Step 6: write results
    write_results(sol, model, config)

    # Step 7: plots
    print("[main] Generating plots...")
    generate_plots(sol, config)

    print("[main] Done. Check results/ directory.")


if __name__ == "__main__":
    main()
