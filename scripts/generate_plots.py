"""
Genera los 4 gráficos PNG en results/ a partir de los CSV de resultados.
Requiere: matplotlib, pandas

Ejecutar DESPUÉS de python main.py:
    python scripts/generate_plots.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from core.config import InstanceConfig
from core.solver import Solution
from views.plots import generate_plots


def _load_solution(results_dir: Path) -> Solution:
    def read(name: str) -> pd.DataFrame:
        p = results_dir / name
        return pd.read_csv(p) if p.exists() else pd.DataFrame()

    bodegas = read("01_Reporte_Bodegas_Abiertas.csv")
    faltante = read("02_Reporte_Faltante.csv")
    inventario = read("03_Reporte_Inventario.csv")
    presupuesto = read("04_Reporte_Presupuesto.csv")
    personal = read("05_Reporte_Personal.csv")
    rutas = read("06_Reporte_Rutas.csv")

    if presupuesto.empty:
        raise FileNotFoundError(
            "No se encontraron resultados en results/. "
            "Ejecuta primero: python main.py"
        )

    return Solution(
        obj_value=0.0, gap=0.0, runtime=0.0, status="LOADED",
        bodegas_abiertas=bodegas,
        faltante=faltante,
        inventario=inventario,
        presupuesto=presupuesto,
        personal=personal,
        rutas=rutas,
    )


if __name__ == "__main__":
    config = InstanceConfig()
    sol = _load_solution(config.results_dir)
    generate_plots(sol, config)
    print(f"[generate_plots] ✓ Gráficos guardados en {config.results_dir}/")
