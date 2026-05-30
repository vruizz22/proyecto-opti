from __future__ import annotations

import matplotlib.pyplot as plt

from core.config import InstanceConfig
from core.solver import Solution

plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"]


def generate_plots(sol: Solution, config: InstanceConfig) -> None:
    config.results_dir.mkdir(exist_ok=True)
    _plot_faltante_prioridad(sol, config)
    _plot_fill_rate_vehiculo(sol, config)
    _plot_presupuesto(sol, config)
    _plot_stock_vs_faltante(sol, config)
    print("[plots] 4 gráficos generados en results/")


def _plot_faltante_prioridad(sol: Solution, config: InstanceConfig) -> None:
    if sol.faltante.empty:
        return
    fig, ax = plt.subplots(figsize=(6, 5))
    falt = sol.faltante.groupby("Prioridad")["Faltante"].sum()
    falt.plot(
        kind="pie", ax=ax,
        autopct="%1.1f%%",
        colors=["#e63946", "#f4a261", "#e9c46a"][: len(falt)],
        startangle=90,
    )
    ax.set_title("Distribución del faltante por prioridad", fontweight="bold")  # type: ignore[union-attr]
    ax.set_ylabel("")  # type: ignore[union-attr]
    fig.tight_layout()
    fig.savefig(config.results_dir / "G1_faltante_prioridad.png", dpi=300)
    plt.close(fig)


def _plot_fill_rate_vehiculo(sol: Solution, config: InstanceConfig) -> None:
    if sol.rutas.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    sol.rutas.boxplot(
        column="Fill_Rate_%",
        by="Vehiculo",
        ax=ax,
        grid=True,
        patch_artist=True)
    ax.axhline(
        y=80,
        color="g",
        linestyle="--",
        alpha=0.6,
        label="Óptimo (>80%)")
    ax.set_title(
        "Tasa de uso de capacidad por tipo de vehículo",
        fontweight="bold")
    ax.set_xlabel("Tipo de vehículo")
    ax.set_ylabel("Fill Rate (%)")
    ax.legend()
    plt.suptitle("")
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout()
    fig.savefig(config.results_dir / "G2_fill_rate_vehiculo.png", dpi=300)
    plt.close(fig)


def _plot_presupuesto(sol: Solution, config: InstanceConfig) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    total = sol.presupuesto["Gasto_CLP"].sum()
    ax.pie(
        sol.presupuesto["Gasto_CLP"],
        labels=sol.presupuesto["Categoria"],
        autopct="%1.1f%%",
        colors=COLORS,
        startangle=90,
    )
    ax.set_title(
        f"Distribución de recursos\n(Total: ${total / 1e6:,.0f} MM CLP)",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(config.results_dir / "G3_presupuesto.png", dpi=300)
    plt.close(fig)


def _plot_stock_vs_faltante(sol: Solution, config: InstanceConfig) -> None:
    if sol.inventario.empty:
        return
    fig, ax1 = plt.subplots(figsize=(9, 5))
    inv_mes = (
        sol.inventario.groupby("Mes")["Stock_Final"]
        .sum()
        .reindex(range(1, 13), fill_value=0)
    )
    inv_mes.plot(
        kind="bar",
        ax=ax1,
        color="#2a9d8f",
        alpha=0.75,
        label="Stock final")
    ax1.set_ylabel("Unidades en stock")
    ax1.set_xlabel("Mes")
    ax1.set_title("Stock vs. Demanda insatisfecha por mes", fontweight="bold")

    if not sol.faltante.empty:
        ax2 = ax1.twinx()
        falt_mes = (
            sol.faltante.groupby("Mes")["Faltante"]
            .sum()
            .reindex(range(1, 13), fill_value=0)
        )
        falt_mes.plot(
            kind="line", ax=ax2, color="#e63946", marker="X",
            linewidth=2, label="Demanda insatisfecha",
        )
        ax2.set_ylabel("Unidades faltantes", color="#e63946")
        ax2.legend(loc="upper right")

    ax1.legend(loc="upper left")
    plt.xticks(rotation=0)
    fig.tight_layout()
    fig.savefig(config.results_dir / "G4_stock_vs_faltante.png", dpi=300)
    plt.close(fig)
