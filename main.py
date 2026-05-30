"""
SENAPRED — Optimización Logística Humanitaria — E4
===================================================
Archivo principal. Ejecutar con:
    python main.py

El script:
  1. Genera datos sintéticos reproducibles en data/ (si no existen).
  2. Carga parámetros desde los CSV.
  3. Construye el modelo Gurobi con R1-R14 (ver core/model_builder.py).
  4. Resuelve con TimeLimit=1800 s (30 min).
  5. Imprime resultados interpretados en consola.
  6. Escribe 6 CSV en results/.
  7. Genera 4 gráficos PNG en results/.

Requiere: gurobipy, pandas, numpy, matplotlib
  pip install -r requirements.txt
"""
from __future__ import annotations
from core.config import InstanceConfig
from core.data_loader import load
from core.model_builder import build_model
from core.sets import build as build_sets

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.solver import solve
from scripts.generate_data import generate
from views.plots import generate_plots
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

    # 7. Gráficos
    generate_plots(sol, config)

    print("\n[main] ✓ Listo. Resultados en results/")


if __name__ == "__main__":
    main()
