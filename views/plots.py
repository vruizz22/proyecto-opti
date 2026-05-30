from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from core.config import InstanceConfig
from core.solver import Solution


def generate_plots(sol: Solution, config: InstanceConfig) -> None:
    config.results_dir.mkdir(exist_ok=True)

    _plot_coverage_by_priority(sol, config)
    _plot_fleet_usage(sol, config)
    _plot_inventory(sol, config)


def _plot_coverage_by_priority(sol: Solution, config: InstanceConfig) -> None:
    if sol.envios.empty and sol.faltantes.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    priorities = config.priorities

    covered: dict[int, float] = {}
    shortage: dict[int, float] = {}
    for p in priorities:
        covered[p] = (
            sol.envios[sol.envios["p"] == p]["x"].sum()
            if not sol.envios.empty
            else 0.0
        )
        shortage[p] = (
            sol.faltantes[sol.faltantes["p"] == p]["f"].sum()
            if not sol.faltantes.empty
            else 0.0
        )

    labels = [f"P{p}" for p in priorities]
    cov_vals = [covered[p] for p in priorities]
    short_vals = [shortage[p] for p in priorities]

    x = range(len(priorities))
    ax.bar(x, cov_vals, label="Cubierto", color="steelblue")
    ax.bar(x, short_vals, bottom=cov_vals, label="Faltante", color="salmon")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Unidades")
    ax.set_title("Cobertura por nivel de prioridad")
    ax.legend()
    fig.tight_layout()
    fig.savefig(config.results_dir / "cobertura_prioridad.png", dpi=150)
    plt.close(fig)


def _plot_fleet_usage(sol: Solution, config: InstanceConfig) -> None:
    if sol.viajes.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    usage = sol.viajes.groupby("m")["n"].sum().sort_values(ascending=False)
    usage.plot(kind="bar", ax=ax, color="steelblue", edgecolor="white")
    ax.set_ylabel("Viajes totales")
    ax.set_title("Uso de flota por tipo de vehículo")
    ax.set_xlabel("Tipo vehículo")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(config.results_dir / "uso_flota.png", dpi=150)
    plt.close(fig)


def _plot_inventory(sol: Solution, config: InstanceConfig) -> None:
    if sol.inventario.empty:
        return

    Kv = list(config.Kv)
    Kn = list(config.Kn)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    for ax, supply_list, title in [
        (axes[0], Kv, "Inventario perecibles (s_{ikt})"),
        (axes[1], Kn, "Inventario no perecibles (s_{ikt})"),
    ]:
        subset = sol.inventario[sol.inventario["k"].isin(supply_list)]
        if subset.empty:
            ax.set_title(f"{title}\n(sin inventario)")
            continue
        pivot = subset.groupby(["t", "k"])["s"].sum().unstack(fill_value=0)
        pivot.plot(ax=ax, marker="o")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Unidades")
        ax.set_title(title)

    fig.tight_layout()
    fig.savefig(config.results_dir / "inventario.png", dpi=150)
    plt.close(fig)
