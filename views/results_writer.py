from __future__ import annotations

import gurobipy as gp

from core.config import InstanceConfig
from core.solver import Solution


def write_results(
        sol: Solution,
        model: gp.Model,
        config: InstanceConfig) -> None:
    config.results_dir.mkdir(exist_ok=True)

    # ── 6 CSV de resultados ───────────────────────────────────────────────
    if not sol.bodegas_abiertas.empty:
        sol.bodegas_abiertas.to_csv(
            config.results_dir / "01_Reporte_Bodegas_Abiertas.csv", index=False
        )
    if not sol.faltante.empty:
        sol.faltante.to_csv(
            config.results_dir / "02_Reporte_Faltante.csv", index=False
        )
    if not sol.inventario.empty:
        sol.inventario.to_csv(
            config.results_dir / "03_Reporte_Inventario.csv", index=False
        )
    sol.presupuesto.to_csv(
        config.results_dir / "04_Reporte_Presupuesto.csv", index=False
    )
    if not sol.personal.empty:
        sol.personal.to_csv(
            config.results_dir / "05_Reporte_Personal.csv", index=False
        )
    if not sol.rutas.empty:
        sol.rutas.to_csv(
            config.results_dir / "06_Reporte_Rutas.csv", index=False
        )

    _print_console(sol, model)


def _print_console(sol: Solution, model: gp.Model) -> None:
    print("\n" + "=" * 65)
    print("SENAPRED — Optimización Logística Humanitaria")
    print("=" * 65)
    print(f"  Estado solver        : {sol.status}")
    print(f"  Función objetivo Z*  : {sol.obj_value:,.2f} minutos-equiv.")
    print(f"  GAP de optimalidad   : {sol.gap * 100:.4f}%")
    print(f"  Tiempo de resolución : {sol.runtime:.2f} s")
    print(f"  Nº variables         : {model.NumVars:,}")
    print(f"  Nº restricciones     : {model.NumConstrs:,}")
    print(f"  Nº no-nulos (matriz) : {model.NumNZs:,}")

    if not sol.bodegas_abiertas.empty:
        bodegas = sol.bodegas_abiertas["Bodega"].tolist()
        print(f"\n  Bodegas habilitadas  : {len(bodegas)} de 12")
        for b in bodegas:
            t = sol.bodegas_abiertas.loc[
                sol.bodegas_abiertas["Bodega"] == b, "Mes_Apertura"
            ].iloc[0]
            print(f"    → {b} (mes {t})")

    pto_total = sol.presupuesto["Gasto_CLP"].sum()
    print(f"\n  Presupuesto utilizado: ${pto_total / 1e6:,.0f} MM CLP")
    for _, row in sol.presupuesto.iterrows():
        pct = row["Gasto_CLP"] / pto_total * 100 if pto_total > 0 else 0
        print(
            f"    {
                row['Categoria']:<12}: ${
                row['Gasto_CLP'] /
                1e6:,.0f} MM ({
                pct:.1f}%)")

    for p in (1, 2, 3):
        if not sol.faltante.empty:
            total = sol.faltante[sol.faltante["Prioridad"]
                                 == p]["Faltante"].sum()
            print(f"\n  Faltante prioridad {p}  : {total:,.0f} unidades")
        else:
            print(f"\n  Faltante prioridad {p}  : 0")

    print("=" * 65)
    print("[results] CSVs escritos en results/")
