"""
Generate all data CSVs for the SENAPRED logistics model.
Data is generated from a fixed seed (reproducible).
Coordinates are real Valparaíso Region locations.
Ranges are justified in E4/main.tex §"Origen de los Datos".

Run: python scripts/generate_data.py
"""
from __future__ import annotations

import sys
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import TypedDict

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import InstanceConfig


# ---------------------------------------------------------------------------
# TypedDicts for structured data
# ---------------------------------------------------------------------------

class BodegaGeo(TypedDict):
    id_bodega: str
    latitud: float
    longitud: float
    tamano: str


class ComunaGeo(TypedDict):
    id_comuna: str
    latitud: float
    longitud: float


class InsumoData(TypedDict):
    insumo: str
    volumen_m3: float
    costo_compra: int
    costo_bodegaje: int
    alpha_s: int
    beta_s: int
    es_perecible: int


class VehiculoData(TypedDict):
    vehiculo: str
    capacidad_m3: float
    tiempo_operativo_min: float
    velocidad_kmh: float
    costo_km_CLP: float


# ---------------------------------------------------------------------------
# Real coordinates — Región de Valparaíso
# ---------------------------------------------------------------------------

BODEGAS_GEO: list[BodegaGeo] = [
    {"id_bodega": "Placilla", "latitud": -33.136, "longitud": -71.569, "tamano": "Grande"},
    {"id_bodega": "Pto_San_Antonio", "latitud": -33.583, "longitud": -71.613, "tamano": "Grande"},
    {"id_bodega": "Barrio_Ind_El_Salto", "latitud": -33.038, "longitud": -71.530, "tamano": "Mediana"},
    {"id_bodega": "Belloto_Sur", "latitud": -33.056, "longitud": -71.411, "tamano": "Mediana"},
    {"id_bodega": "Base_Torquemada", "latitud": -32.949, "longitud": -71.478, "tamano": "Mediana"},
    {"id_bodega": "Ruta_60CH_Quillota", "latitud": -32.890, "longitud": -71.250, "tamano": "Mediana"},
    {"id_bodega": "Parque_Ind_San_Felipe", "latitud": -32.750, "longitud": -70.720, "tamano": "Mediana"},
    {"id_bodega": "Pto_Quintero", "latitud": -32.778, "longitud": -71.520, "tamano": "Mediana"},
    {"id_bodega": "Aerodromo_Rodelillo", "latitud": -33.064, "longitud": -71.564, "tamano": "Pequeña"},
    {"id_bodega": "Casablanca_Centro", "latitud": -33.318, "longitud": -71.406, "tamano": "Pequeña"},
    {"id_bodega": "Estadio_Limache", "latitud": -33.001, "longitud": -71.264, "tamano": "Pequeña"},
    {"id_bodega": "La_Ligua", "latitud": -32.450, "longitud": -71.233, "tamano": "Pequeña"},
]

COMUNAS_GEO: list[ComunaGeo] = [
    {"id_comuna": "Valparaiso", "latitud": -33.045, "longitud": -71.620},
    {"id_comuna": "Vina_del_Mar", "latitud": -33.024, "longitud": -71.551},
    {"id_comuna": "Quilpue", "latitud": -33.049, "longitud": -71.442},
    {"id_comuna": "Villa_Alemana", "latitud": -33.042, "longitud": -71.374},
    {"id_comuna": "Concon", "latitud": -32.923, "longitud": -71.516},
    {"id_comuna": "Quintero", "latitud": -32.778, "longitud": -71.532},
    {"id_comuna": "Puchuncavi", "latitud": -32.730, "longitud": -71.411},
    {"id_comuna": "Limache", "latitud": -32.997, "longitud": -71.263},
    {"id_comuna": "Olmue", "latitud": -33.000, "longitud": -71.183},
    {"id_comuna": "Quillota", "latitud": -32.880, "longitud": -71.248},
    {"id_comuna": "La_Cruz", "latitud": -32.828, "longitud": -71.226},
    {"id_comuna": "La_Calera", "latitud": -32.783, "longitud": -71.213},
    {"id_comuna": "Casablanca", "latitud": -33.316, "longitud": -71.407},
    {"id_comuna": "San_Antonio", "latitud": -33.593, "longitud": -71.611},
    {"id_comuna": "Cartagena", "latitud": -33.553, "longitud": -71.605},
    {"id_comuna": "El_Quisco", "latitud": -33.391, "longitud": -71.695},
    {"id_comuna": "Algarrobo", "latitud": -33.366, "longitud": -71.666},
    {"id_comuna": "Llaillay", "latitud": -32.842, "longitud": -70.952},
    {"id_comuna": "San_Felipe", "latitud": -32.750, "longitud": -70.725},
    {"id_comuna": "Los_Andes", "latitud": -32.836, "longitud": -70.596},
]

# Comunas con topografía de cerros — restricción de carga pesada
CERRO_COMMUNES: frozenset[str] = frozenset(
    {"Valparaiso", "Puchuncavi", "El_Quisco", "Cartagena", "Algarrobo"}
)

# Insumos con parámetros base
INSUMOS: list[InsumoData] = [
    {"insumo": "Agua_5L", "volumen_m3": 0.005, "costo_compra": 1500,
     "costo_bodegaje": 75, "alpha_s": 6, "beta_s": 6, "es_perecible": 1},
    {"insumo": "Racion_24h_Familiar", "volumen_m3": 0.015, "costo_compra": 12000,
     "costo_bodegaje": 600, "alpha_s": 10, "beta_s": 10, "es_perecible": 1},
    {"insumo": "Kit_Medico_Trauma", "volumen_m3": 0.010, "costo_compra": 45000,
     "costo_bodegaje": 2250, "alpha_s": 12, "beta_s": 12, "es_perecible": 1},
    {"insumo": "Medicamentos_Cronicos", "volumen_m3": 0.002, "costo_compra": 25000,
     "costo_bodegaje": 1250, "alpha_s": 7, "beta_s": 7, "es_perecible": 1},
    {"insumo": "Suplementos_Pediatricos", "volumen_m3": 0.003, "costo_compra": 18000,
     "costo_bodegaje": 900, "alpha_s": 8, "beta_s": 8, "es_perecible": 1},
    {"insumo": "Kit_Higiene_Familiar", "volumen_m3": 0.012, "costo_compra": 22000,
     "costo_bodegaje": 1100, "alpha_s": 9, "beta_s": 9, "es_perecible": 0},
    {"insumo": "Frazadas_Termicas", "volumen_m3": 0.020, "costo_compra": 8500,
     "costo_bodegaje": 425, "alpha_s": 11, "beta_s": 11, "es_perecible": 0},
    {"insumo": "Carpas_Refugio", "volumen_m3": 0.080, "costo_compra": 85000,
     "costo_bodegaje": 4250, "alpha_s": 14, "beta_s": 14, "es_perecible": 0},
    {"insumo": "Herramientas_Remocion", "volumen_m3": 0.050, "costo_compra": 35000,
     "costo_bodegaje": 1750, "alpha_s": 13, "beta_s": 13, "es_perecible": 0},
    {"insumo": "Mascarillas_N95", "volumen_m3": 0.005, "costo_compra": 8000,
     "costo_bodegaje": 400, "alpha_s": 5, "beta_s": 5, "es_perecible": 0},
    {"insumo": "Generador_Portatil", "volumen_m3": 0.150, "costo_compra": 350000,
     "costo_bodegaje": 17500, "alpha_s": 15, "beta_s": 15, "es_perecible": 0},
    {"insumo": "Baterias_D", "volumen_m3": 0.001, "costo_compra": 4500,
     "costo_bodegaje": 225, "alpha_s": 5, "beta_s": 5, "es_perecible": 0},
]

VEHICULOS: list[VehiculoData] = [
    {"vehiculo": "Camioneta_4x4", "capacidad_m3": 2.5,
     "tiempo_operativo_min": 5.0, "velocidad_kmh": 65.0, "costo_km_CLP": 690.0},
    {"vehiculo": "Camion_3_4", "capacidad_m3": 18.0,
     "tiempo_operativo_min": 10.0, "velocidad_kmh": 55.0, "costo_km_CLP": 1020.0},
    {"vehiculo": "Camion_Pesado", "capacidad_m3": 45.0,
     "tiempo_operativo_min": 20.0, "velocidad_kmh": 45.0, "costo_km_CLP": 2620.0},
    {"vehiculo": "Helicoptero", "capacidad_m3": 4.0,
     "tiempo_operativo_min": 15.0, "velocidad_kmh": 150.0, "costo_km_CLP": 14000.0},
]

# Demanda base por insumo (unidades anuales para todo el radio, se
# distribuye por comuna)
DEMANDA_BASE: dict[str, int] = {
    "Agua_5L": 120000,
    "Racion_24h_Familiar": 45000,
    "Kit_Medico_Trauma": 8000,
    "Medicamentos_Cronicos": 12000,
    "Suplementos_Pediatricos": 6000,
    "Kit_Higiene_Familiar": 30000,
    "Frazadas_Termicas": 25000,
    "Carpas_Refugio": 3000,
    "Herramientas_Remocion": 2000,
    "Mascarillas_N95": 50000,
    "Generador_Portatil": 500,
    "Baterias_D": 40000,
}

# Peso por comuna (basado en vulnerabilidad FIBE: 78% en Viña, Quilpué, Villa Alemana)
# Los_Andes: ~70.000 hab. en zona de interfaz forestal cordillerana.
COMUNA_WEIGHT: dict[str, float] = {
    "Valparaiso": 0.120, "Vina_del_Mar": 0.130, "Quilpue": 0.115,
    "Villa_Alemana": 0.100, "Concon": 0.040, "Quintero": 0.035,
    "Puchuncavi": 0.030, "Limache": 0.050, "Olmue": 0.030,
    "Quillota": 0.060, "La_Cruz": 0.025, "La_Calera": 0.045,
    "Casablanca": 0.035, "San_Antonio": 0.060, "Cartagena": 0.030,
    "El_Quisco": 0.020, "Algarrobo": 0.020, "Llaillay": 0.025,
    "San_Felipe": 0.030, "Los_Andes": 0.030,
}

# Factor estacional — alta demanda en verano (incendios)
SEASONAL_FACTOR: dict[int, float] = {
    1: 3.5, 2: 4.0, 3: 3.0,    # verano: incendios
    4: 0.4, 5: 0.3, 6: 0.3,    # otoño-invierno: baja
    7: 0.3, 8: 0.3, 9: 0.4,    # invierno-primavera
    10: 0.5, 11: 0.8, 12: 3.2,  # pre-verano
}

# Peso de demanda por prioridad para cada insumo
PRIORITY_DIST: dict[str, dict[int, float]] = {
    "Agua_5L": {1: 0.55, 2: 0.30, 3: 0.15},
    "Racion_24h_Familiar": {1: 0.40, 2: 0.35, 3: 0.25},
    "Kit_Medico_Trauma": {1: 0.65, 2: 0.25, 3: 0.10},
    "Medicamentos_Cronicos": {1: 0.60, 2: 0.30, 3: 0.10},
    "Suplementos_Pediatricos": {1: 0.50, 2: 0.35, 3: 0.15},
    "Kit_Higiene_Familiar": {1: 0.25, 2: 0.45, 3: 0.30},
    "Frazadas_Termicas": {1: 0.20, 2: 0.45, 3: 0.35},
    "Carpas_Refugio": {1: 0.15, 2: 0.40, 3: 0.45},
    "Herramientas_Remocion": {1: 0.10, 2: 0.35, 3: 0.55},
    "Mascarillas_N95": {1: 0.30, 2: 0.40, 3: 0.30},
    "Generador_Portatil": {1: 0.20, 2: 0.40, 3: 0.40},
    "Baterias_D": {1: 0.25, 2: 0.40, 3: 0.35},
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * \
        cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def generate(config: InstanceConfig | None = None) -> None:
    cfg = config or InstanceConfig()
    rng = np.random.default_rng(cfg.seed)
    out = cfg.data_dir
    out.mkdir(exist_ok=True)

    # ── 1. bodegas_candidatas.csv ──────────────────────────────────────────
    size_params: dict[str, dict[str, object]] = {
        "Grande": {"cap_range": (7000, 9500), "cost_range": (45_000_000, 60_000_000), "pmin": 15, "pmax": 50},
        "Mediana": {"cap_range": (3000, 4500), "cost_range": (25_000_000, 35_000_000), "pmin": 6, "pmax": 25},
        "Pequeña": {"cap_range": (1000, 1600), "cost_range": (10_000_000, 15_000_000), "pmin": 3, "pmax": 12},
    }
    rows_bod: list[dict[str, object]] = []
    for b in BODEGAS_GEO:
        sp = size_params[b["tamano"]]
        cap_lo, cap_hi = int(sp["cap_range"][0]), int(
            sp["cap_range"][1])  # type: ignore[index]
        cost_lo, cost_hi = int(
            sp["cost_range"][0]), int(
            sp["cost_range"][1])  # type: ignore[index]
        rows_bod.append({
            "id_bodega": b["id_bodega"],
            "latitud": b["latitud"],
            "longitud": b["longitud"],
            "tamano": b["tamano"],
            "capacidad_m3": int(rng.integers(cap_lo, cap_hi + 1)),
            "costo_fijo_CLP": int(rng.integers(cost_lo, cost_hi + 1)),
            "personal_min": int(sp["pmin"]),  # type: ignore[arg-type]
            "personal_max": int(sp["pmax"]),  # type: ignore[arg-type]
        })
    pd.DataFrame(rows_bod).to_csv(out / "bodegas_candidatas.csv", index=False)

    # ── 2. comunas_demandantes.csv ─────────────────────────────────────────
    pd.DataFrame(COMUNAS_GEO).to_csv(
        out / "comunas_demandantes.csv", index=False)

    # ── 3. insumos.csv ─────────────────────────────────────────────────────
    ins_rows: list[dict[str, object]] = []
    for ins in INSUMOS:
        alpha_min = ins["alpha_s"] / 60.0
        beta_min = ins["beta_s"] / 60.0
        ins_rows.append({
            "insumo": ins["insumo"],
            "volumen_m3": ins["volumen_m3"],
            "costo_compra_CLP": ins["costo_compra"],
            "costo_bodegaje_CLP_mes": ins["costo_bodegaje"],
            "alpha_min": round(alpha_min, 5),
            "beta_min": round(beta_min, 5),
            "es_perecible": ins["es_perecible"],
        })
    pd.DataFrame(ins_rows).to_csv(out / "insumos.csv", index=False)

    # ── 4. vehiculos.csv ───────────────────────────────────────────────────
    pd.DataFrame(VEHICULOS)[["vehiculo", "capacidad_m3", "tiempo_operativo_min"]].to_csv(
        out / "vehiculos.csv", index=False)

    # ── 5. ponderadores.csv ────────────────────────────────────────────────
    pd.DataFrame([
        {"prioridad": 1, "W_p": 100.0, "pi_p": 20000.0},
        {"prioridad": 2, "W_p": 10.0, "pi_p": 5000.0},
        {"prioridad": 3, "W_p": 1.0, "pi_p": 1000.0},
    ]).to_csv(out / "ponderadores.csv", index=False)

    # ── 6. parametros_globales.csv ─────────────────────────────────────────
    pd.DataFrame([
        {"param": "rho", "valor": 0.75},
        {"param": "d_horas_mes", "valor": 360.0},
        {"param": "presupuesto_B", "valor": 5_000_000_000.0},
        {"param": "factor_h", "valor": 0.0001},
        {"param": "sueldo_mensual", "valor": 850_000.0},
    ]).to_csv(out / "parametros_globales.csv", index=False)

    # ── 7. flota_disponible.csv — Q_{mt} ───────────────────────────────────
    flota_base: dict[str, int] = {
        "Camioneta_4x4": 30, "Camion_3_4": 15, "Camion_Pesado": 8, "Helicoptero": 3
    }
    rows_q: list[dict[str, object]] = []
    for m in cfg.vehicle_ids:
        for t in cfg.T:
            rows_q.append({"vehiculo": m, "mes": t,
                          "cantidad_max": flota_base[m]})
    pd.DataFrame(rows_q).to_csv(out / "flota_disponible.csv", index=False)

    # ── 8. stock_inicial.csv — S0_{ik} ─────────────────────────────────────
    rows_s0: list[dict[str, object]] = []
    for b in BODEGAS_GEO:
        for ins in INSUMOS:
            val = 0 if ins["es_perecible"] else int(rng.integers(0, 31))
            rows_s0.append(
                {"id_bodega": b["id_bodega"], "insumo": ins["insumo"], "stock_inicial": val})
    pd.DataFrame(rows_s0).to_csv(out / "stock_inicial.csv", index=False)

    # ── 9. matriz_transporte.csv ───────────────────────────────────────────
    # Road factor: terrestrial distance = haversine × 1.4 (Valparaíso topography — MOP)
    # Air: straight-line haversine (no road factor)
    ROAD_FACTOR = 1.40
    veh_info: dict[str, dict[str, float]] = {
        v["vehiculo"]: {"vel": v["velocidad_kmh"], "cpkm": v["costo_km_CLP"]}
        for v in VEHICULOS
    }

    rows_tr: list[dict[str, object]] = []
    for b in BODEGAS_GEO:
        for c in COMUNAS_GEO:
            air_km = _haversine_km(b["latitud"], b["longitud"],
                                   c["latitud"], c["longitud"])
            road_km = air_km * ROAD_FACTOR
            alt_km = road_km * 1.25  # ruta alternativa es 25% más larga

            for veh in ["Camioneta_4x4", "Camion_3_4", "Camion_Pesado"]:
                vel = veh_info[veh]["vel"]
                cpkm = veh_info[veh]["cpkm"]
                t_princ = road_km / vel * 60.0
                c_princ = road_km * cpkm
                # Camion_Pesado no apto en rutas de cerros (aptitud = 0 en
                # Alternativa)
                apt_alt = 0 if (
                    veh == "Camion_Pesado" and c["id_comuna"] in CERRO_COMMUNES) else 1
                rows_tr.append({
                    "id_bodega": b["id_bodega"], "id_comuna": c["id_comuna"],
                    "ruta": "Principal", "vehiculo": veh,
                    "tiempo_min": round(t_princ, 1),
                    "costo_viaje_CLP": round(c_princ),
                    "aptitud": 1,
                })
                t_alt = alt_km / vel * 60.0
                c_alt = alt_km * cpkm
                rows_tr.append({
                    "id_bodega": b["id_bodega"], "id_comuna": c["id_comuna"],
                    "ruta": "Alternativa", "vehiculo": veh,
                    "tiempo_min": round(t_alt, 1),
                    "costo_viaje_CLP": round(c_alt),
                    "aptitud": apt_alt,
                })
            # Helicóptero — solo ruta Aérea
            vel_h = veh_info["Helicoptero"]["vel"]
            cpkm_h = veh_info["Helicoptero"]["cpkm"]
            t_aerea = air_km / vel_h * 60.0
            c_aerea = air_km * cpkm_h
            rows_tr.append({
                "id_bodega": b["id_bodega"], "id_comuna": c["id_comuna"],
                "ruta": "Aerea", "vehiculo": "Helicoptero",
                "tiempo_min": round(t_aerea, 1),
                "costo_viaje_CLP": round(c_aerea),
                "aptitud": 1,
            })

    pd.DataFrame(rows_tr).to_csv(out / "matriz_transporte.csv", index=False)

    # ── 10. demanda_proyectada.csv ─────────────────────────────────────────
    rows_d: list[dict[str, object]] = []
    for c in COMUNAS_GEO:
        jname = c["id_comuna"]
        w_j = COMUNA_WEIGHT[jname]
        for ins in INSUMOS:
            k = ins["insumo"]
            base_anual = DEMANDA_BASE[k] * w_j
            for t in range(1, 13):
                sf = SEASONAL_FACTOR[t]
                noise = float(rng.uniform(0.85, 1.15))
                base_mes = base_anual / 12.0 * sf * noise
                for p in (1, 2, 3):
                    pdist = PRIORITY_DIST[k][p]
                    val = max(0, round(base_mes * pdist))
                    rows_d.append({
                        "id_comuna": jname, "insumo": k,
                        "mes": t, "prioridad": p,
                        "cantidad_unidades": val,
                    })
    pd.DataFrame(rows_d).to_csv(out / "demanda_proyectada.csv", index=False)

    print(
        f"[generate_data] {len(list(out.glob('*.csv')))} CSVs escritos en {out}/")
    print(
        f"  Bodegas: {
            len(BODEGAS_GEO)} | Comunas: {
            len(COMUNAS_GEO)} | Insumos: {
                len(INSUMOS)}")
    print(
        f"  Filas matriz_transporte: {
            len(rows_tr)} | Filas demanda: {
            len(rows_d)}")


if __name__ == "__main__":
    generate()
