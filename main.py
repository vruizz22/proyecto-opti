"""
SENAPRED — Optimización Logística Humanitaria — E4
===================================================
Ejecutar con:  python main.py

El script:
  1. Genera datos sintéticos reproducibles en data/ (si no existen).
  2. Carga parámetros desde los CSV.
  3. Construye el modelo Gurobi con R1-R14 (ver core/model_builder.py).
  4. Resuelve con TimeLimit=1800 s (30 min).
  5. Imprime resultados en consola.
  6. Escribe 6 CSV en results/.

Para generar gráficos y PDF de análisis (requiere matplotlib):
  python scripts/generate_plots.py
  python scripts/generate_pdf.py

Requiere solo: gurobipy, pandas, numpy
"""
from __future__ import annotations
from scripts.generate_data import generate
from core.solver import solve
from core.sets import build as build_sets
from core.model_builder import build_model
from core.data_loader import load
from core.config import InstanceConfig

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from views.results_writer import write_results


def main() -> None:
    config = InstanceConfig()
    config.results_dir.mkdir(exist_ok=True)

    # 1. Generar datos si no existen
    if not (config.data_dir / "demanda_proyectada.csv").exists():
        print("[main] Generando datos sintéticos (semilla fija)...")
        generate(config)
    else:
        print("[main] Datos encontrados en data/")

    # 2. Cargar parámetros
    print("[main] Cargando parámetros...")
    params = load(config)

    # 3. Construir conjuntos dispersos
    print("[main] Construyendo conjuntos (R', F_p, Apt)...")
    sets = build_sets(config, params)
    print(f"       trip_keys={len(sets.trip_keys):,}  "
          f"flow_keys={len(sets.flow_keys):,}  "
          f"short_keys={len(sets.short_keys):,}")

    # 4. Construir modelo
    print("[main] Construyendo modelo...")
    model, mv = build_model(sets, params, config)
    nv, nc, nz = model.NumVars, model.NumConstrs, model.NumNZs
    print(f"       NumVars={nv:,}  NumConstrs={nc:,}  NumNZs={nz:,}")

    # 5. Resolver
    print(f"[main] Resolviendo (TimeLimit={config.time_limit_s:.0f} s)...")
    sol = solve(model, mv, config, sets, params)

    # 6. Escribir resultados
    write_results(sol, model, config)

    print("\n[main] ✓ Listo. Resultados en results/")
    print("[main]   Para gráficos: python scripts/generate_plots.py")
    print("[main]   Para PDF:      python scripts/generate_pdf.py")


if __name__ == "__main__":
    main()
