"""
Build all index sets and sparse tuplelist keys for the model.
R'_{ijm} is already collapsed in data_loader (min-time route per mode).
flow_keys and trip_keys cover all 12 months where feasibility holds.
Structural sparsity: variables only exist where Apt=1, T+O≤T^max_p, D>0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import gurobipy as gp

from core.config import InstanceConfig
from core.parameters import Parameters

# gp.tuplelist es subclase de list; usamos este alias para que Pylance
# acepte len(), iteración y las anotaciones sin errores de tipo parcial.
TupleList = list[tuple[Any, ...]]


@dataclass(frozen=True)
class Sets:
    I: list[str]
    J: list[str]
    K: list[str]
    M: list[str]
    T: list[int]
    P: list[int]
    Kv: list[str]
    Kn: list[str]

    # En runtime son gp.tuplelist (subclase de list) para usar .select()
    trip_keys: TupleList   # (i,j,m,t,p)
    flow_keys: TupleList   # (i,j,k,m,t,p)
    short_keys: TupleList  # (j,k,t,p)


def build(config: InstanceConfig, params: Parameters) -> Sets:
    I = list(config.I)
    J = list(config.J)
    K = list(config.K)
    M = list(config.M)
    T = list(config.T)
    P = list(config.P)
    Kv = list(config.Kv)
    Kn = list(config.Kn)

    t_max = config.t_max_minutes

    # Pre-compute O(1) lookups
    o_raw: dict[Any, Any] = dict(params.O.items())
    o_dict: dict[str, float] = {str(k): float(v) for k, v in o_raw.items()}
    t_travel_raw: dict[Any, Any] = dict(params.T_travel.items())
    t_travel_dict: dict[tuple[str, str, str], float] = {
        (str(k[0]), str(k[1]), str(k[2])): float(v)
        for k, v in t_travel_raw.items()
    }

    # Demand index: only (j,k,t,p) where D > 0
    demand_raw: dict[Any, Any] = dict(params.D.items())
    demand_pos: set[tuple[str, str, int, int]] = {
        (str(k[0]), str(k[1]), int(k[2]), int(k[3]))
        for k, v in demand_raw.items()
        if float(v) > 0.0
    }

    # trip_keys: (i,j,m,t,p) where R'_{ijm} exists AND T_{ijm}+O_m <= T^max_p
    # AND there is demand in commune j at any supply for this (t,p)
    demand_jtp: set[tuple[str, int, int]] = {
        (j, t, p) for (j, _, t, p) in demand_pos}

    trip_set: set[tuple[str, str, str, int, int]] = set()
    for i in I:
        for j in J:
            for m in M:
                tt = t_travel_dict.get((i, j, m))
                if tt is None:
                    continue  # (i,j,m) not in R' (no apt route)
                o_m = o_dict[m]
                for t in T:
                    for p in P:
                        if tt + o_m <= t_max[p] and (j, t, p) in demand_jtp:
                            trip_set.add((i, j, m, t, p))

    trip_keys: gp.tuplelist = gp.tuplelist(sorted(trip_set))  # type: ignore[type-arg]

    # flow_keys: (i,j,k,m,t,p) where trip (i,j,m,t,p) feasible AND D_{jktp} > 0
    flow_set: set[tuple[str, str, str, str, int, int]] = set()
    for (i, j, m, t, p) in trip_keys:
        for k in K:
            if (j, k, t, p) in demand_pos:
                flow_set.add((i, j, k, m, t, p))

    flow_keys: gp.tuplelist = gp.tuplelist(sorted(flow_set))  # type: ignore[type-arg]

    # short_keys: (j,k,t,p) where D > 0
    short_keys: gp.tuplelist = gp.tuplelist(
        sorted(demand_pos))  # type: ignore[type-arg]

    return Sets(
        I=I, J=J, K=K, M=M, T=T, P=P, Kv=Kv, Kn=Kn,
        trip_keys=trip_keys,
        flow_keys=flow_keys,
        short_keys=short_keys,
    )
