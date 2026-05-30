from __future__ import annotations

from pathlib import Path

import gurobipy as gp
import pandas as pd

from core.config import InstanceConfig
from core.solver import Solution


def write_results(
    sol: Solution,
    model: gp.Model,
    config: InstanceConfig,
) -> None:
    config.results_dir.mkdir(exist_ok=True)
    xlsx_path = config.results_dir / "resultados.xlsx"

    n_vars = model.NumVars
    n_constrs = model.NumConstrs

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # Resumen
        resumen = pd.DataFrame([
            {"Métrica": "Función objetivo (min-equiv)", "Valor": round(sol.obj_value, 2)},
            {"Métrica": "GAP MIP (%)", "Valor": round(sol.gap * 100, 4)},
            {"Métrica": "Tiempo resolución (s)", "Valor": round(sol.runtime, 1)},
            {"Métrica": "Estado", "Valor": sol.status},
            {"Métrica": "Nº variables", "Valor": n_vars},
            {"Métrica": "Nº restricciones", "Valor": n_constrs},
        ])
        resumen.to_excel(writer, sheet_name="Resumen", index=False)

        # Bodegas
        if not sol.bodegas.empty:
            sol.bodegas.to_excel(writer, sheet_name="Bodegas", index=False)

        # Compras e Inventario
        if not sol.inventario.empty:
            sol.inventario.to_excel(writer, sheet_name="Inventario", index=False)

        # Envíos
        if not sol.envios.empty:
            sol.envios.to_excel(writer, sheet_name="Envíos", index=False)

        # Viajes
        if not sol.viajes.empty:
            sol.viajes.to_excel(writer, sheet_name="Viajes", index=False)

        # Faltantes
        if not sol.faltantes.empty:
            sol.faltantes.to_excel(writer, sheet_name="Faltantes", index=False)

    print(f"\n[results] Resultados escritos en {xlsx_path}")
    _print_summary(sol, config)


def _print_summary(sol: Solution, config: InstanceConfig) -> None:
    commune_names = config.commune_names
    print("\n" + "=" * 60)
    print("RESUMEN EJECUTIVO — SENAPRED Logística Humanitaria")
    print("=" * 60)
    print(f"Función objetivo total:   {sol.obj_value:,.0f} min-equiv")
    print(f"Estado del solver:        {sol.status}")
    print(f"Tiempo de resolución:     {sol.runtime:.1f} s")

    if not sol.bodegas.empty:
        open_i = sol.bodegas[sol.bodegas["w"] == 1]["i"].unique().tolist()
        print(f"Bodegas habilitadas:      {open_i}")

    if not sol.faltantes.empty:
        total_short = sol.faltantes["f"].sum()
        print(f"Faltante total:           {total_short:,.0f} unidades")
    else:
        print("Faltante total:           0 — demanda cubierta completamente")

    if not sol.envios.empty:
        for j_idx, jname in enumerate(commune_names):
            vol = sol.envios[sol.envios["j"] == j_idx]["x"].sum()
            if vol > 0:
                print(f"  → {jname}: {vol:,.0f} unidades enviadas")

    print("=" * 60)
