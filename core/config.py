from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

WAREHOUSE_IDS: tuple[str, ...] = (
    "Placilla",
    "Pto_San_Antonio",
    "Barrio_Ind_El_Salto",
    "Belloto_Sur",
    "Base_Torquemada",
    "Ruta_60CH_Quillota",
    "Parque_Ind_San_Felipe",
    "Pto_Quintero",
    "Aerodromo_Rodelillo",
    "Casablanca_Centro",
    "Estadio_Limache",
    "La_Ligua",
)

COMMUNE_IDS: tuple[str, ...] = (
    "Valparaiso",
    "Vina_del_Mar",
    "Quilpue",
    "Villa_Alemana",
    "Concon",
    "Quintero",
    "Puchuncavi",
    "Limache",
    "Olmue",
    "Quillota",
    "La_Cruz",
    "La_Calera",
    "Casablanca",
    "San_Antonio",
    "Cartagena",
    "El_Quisco",
    "Algarrobo",
    "Llaillay",
    "San_Felipe",
)

SUPPLY_IDS: tuple[str, ...] = (
    # Perecibles (K_v)
    "Agua_5L",
    "Racion_24h_Familiar",
    "Kit_Medico_Trauma",
    "Medicamentos_Cronicos",
    "Suplementos_Pediatricos",
    # No perecibles (K_n)
    "Kit_Higiene_Familiar",
    "Frazadas_Termicas",
    "Carpas_Refugio",
    "Herramientas_Remocion",
    "Mascarillas_N95",
    "Generador_Portatil",
    "Baterias_D",
)

VEHICLE_IDS: tuple[str, ...] = (
    "Camioneta_4x4",
    "Camion_3_4",
    "Camion_Pesado",
    "Helicoptero",
)

ROUTE_IDS: tuple[str, ...] = ("Principal", "Alternativa", "Aerea")

PERISHABLE: frozenset[str] = frozenset({
    "Agua_5L",
    "Racion_24h_Familiar",
    "Kit_Medico_Trauma",
    "Medicamentos_Cronicos",
    "Suplementos_Pediatricos",
})

# Warehouse size category: id_bodega -> g ∈ {1=Pequeña, 2=Mediana, 3=Grande}
WAREHOUSE_CATEGORY: dict[str, int] = {
    "Placilla": 3,
    "Pto_San_Antonio": 3,
    "Barrio_Ind_El_Salto": 2,
    "Belloto_Sur": 2,
    "Base_Torquemada": 2,
    "Ruta_60CH_Quillota": 2,
    "Parque_Ind_San_Felipe": 2,
    "Pto_Quintero": 2,
    "Aerodromo_Rodelillo": 1,
    "Casablanca_Centro": 1,
    "Estadio_Limache": 1,
    "La_Ligua": 1,
}


@dataclass(frozen=True, slots=True)
class InstanceConfig:
    # Sets
    warehouse_ids: tuple[str, ...] = WAREHOUSE_IDS
    commune_ids: tuple[str, ...] = COMMUNE_IDS
    supply_ids: tuple[str, ...] = SUPPLY_IDS
    vehicle_ids: tuple[str, ...] = VEHICLE_IDS
    route_ids: tuple[str, ...] = ROUTE_IDS
    perishable: frozenset[str] = field(default_factory=lambda: PERISHABLE)
    warehouse_category: dict[str, int] = field(
        default_factory=lambda: WAREHOUSE_CATEGORY)

    horizon_months: int = 12
    priorities: tuple[int, ...] = (1, 2, 3)

    # T^max_p [min] — Esfera 2018: p1 ≤ 45 min, p2 ≤ 120, p3 ≤ 240
    t_max_minutes: dict[int, float] = field(
        default_factory=lambda: {1: 45.0, 2: 120.0, 3: 240.0}
    )

    # Solver
    seed: int = 1113
    time_limit_s: float = 1800.0
    mip_gap: float = 0.0

    # Gurobi WLS — credenciales del grupo (licencia Online Course sin cap
    # local)
    wls_access_id: str = "d1d2087a-5595-4edc-8c56-86b291b3d5b3"
    wls_secret: str = "087e5baa-b338-47f3-81ed-539ca3f6da57"
    wls_license_id: int = 2827565

    # Paths
    data_dir: Path = field(default_factory=lambda: BASE_DIR / "data")
    results_dir: Path = field(default_factory=lambda: BASE_DIR / "results")

    @property
    def I(self) -> tuple[str, ...]:
        return self.warehouse_ids

    @property
    def J(self) -> tuple[str, ...]:
        return self.commune_ids

    @property
    def K(self) -> tuple[str, ...]:
        return self.supply_ids

    @property
    def M(self) -> tuple[str, ...]:
        return self.vehicle_ids

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
        return frozenset(self.supply_ids) - self.perishable
