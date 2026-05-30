from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


@dataclass(frozen=True, slots=True)
class InstanceConfig:
    # Sets
    n_warehouses: int = 3
    n_communes: int = 5
    commune_names: tuple[str, ...] = (
        "Viña del Mar",
        "Quilpué",
        "Villa Alemana",
        "Valparaíso",
        "Limache",
    )
    warehouse_sizes: tuple[int, ...] = (1, 2, 3)  # g ∈ G = {1,2,3}
    vehicle_types: tuple[str, ...] = (
        "camion",
        "camioneta",
        "ambulancia",
        "helicoptero",
        "avioneta",
    )
    supplies: tuple[str, ...] = (
        "agua",
        "alimentos",
        "medicamentos",
        "frazadas",
        "baterias",
        "radios",
        "higiene",
    )
    perishable: frozenset[str] = field(
        default_factory=lambda: frozenset({"alimentos", "medicamentos"})
    )
    horizon_months: int = 12
    fire_months: tuple[int, ...] = (1, 2, 12)
    priorities: tuple[int, ...] = (1, 2, 3)

    # Solver
    seed: int = 1113
    time_limit_s: float = 1800.0
    mip_gap: float = 0.0

    # Paths
    data_dir: Path = field(default_factory=lambda: BASE_DIR / "data")
    results_dir: Path = field(default_factory=lambda: BASE_DIR / "results")

    # T^max_p [min] — Esfera 2018
    t_max_minutes: dict[int, float] = field(
        default_factory=lambda: {1: 60.0, 2: 180.0, 3: 480.0}
    )

    # priority_of_supply k -> p
    priority_of_supply: dict[str, int] = field(
        default_factory=lambda: {
            "agua": 1,
            "medicamentos": 1,
            "alimentos": 2,
            "frazadas": 2,
            "radios": 3,
            "baterias": 3,
            "higiene": 3,
        }
    )

    def __post_init__(self) -> None:
        assert len(self.commune_names) == self.n_communes
        assert len(self.warehouse_sizes) == self.n_warehouses

    @property
    def I(self) -> range:
        return range(self.n_warehouses)

    @property
    def J(self) -> range:
        return range(self.n_communes)

    @property
    def K(self) -> tuple[str, ...]:
        return self.supplies

    @property
    def M(self) -> tuple[str, ...]:
        return self.vehicle_types

    @property
    def T(self) -> range:
        return range(1, self.horizon_months + 1)

    @property
    def P(self) -> tuple[int, ...]:
        return self.priorities

    @property
    def Kv(self) -> frozenset[str]:
        return self.perishable

    @property
    def Kn(self) -> frozenset[str]:
        return frozenset(self.supplies) - self.perishable
