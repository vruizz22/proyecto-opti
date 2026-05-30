"""
Build all index sets and sparse tuplelist keys for the model.
R'_{ijm} is collapsed to singleton (minimum-time route per mode).
Aptitude, temporal feasibility (F_p) and demand existence are imposed
STRUCTURALLY by excluding infeasible tuples from flow_keys / trip_keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import gurobipy as gp
import pandas as pd

from core.config import InstanceConfig
from core.parameters import Parameters


@dataclass(frozen=True)
class Sets:
    I: list[int]
    J: list[int]
    K: list[str]
    M: list[str]
    T: list[int]
    P: list[int]
    Kv: list[str]
    Kn: list[str]
    T_dem: list[int]  # fire months only

    # i -> g mapping
    Ig: dict[int, int]  # i -> g (warehouse size category)

    # Collapsed route: (i,j,m) -> route_id (always 0 — singleton)
    R_prime: dict[tuple[int, int, str], int]

    # Sparse keys for flow variables x_{ijkmtp}
    flow_keys: gp.tuplelist  # type: ignore[type-arg]

    # Sparse keys for trip variable n_{ijmtp}
    trip_keys: gp.tuplelist  # type: ignore[type-arg]

    # Keys for shortage variable f_{jktp}
    short_keys: gp.tuplelist  # type: ignore[type-arg]


def build(config: InstanceConfig, params: Parameters) -> Sets:
    I = list(config.I)
    J = list(config.J)
    K = list(config.K)
    M = list(config.M)
    T = list(config.T)
    P = list(config.P)
    Kv = list(config.Kv)
    Kn = list(config.Kn)
    T_dem = list(config.fire_months)

    # i -> g
    Ig: dict[int, int] = {int(i): int(params.warehouse_g[i]) for i in I}

    # R'_{ijm}: singleton route id = 0 for all valid (i,j,m)
    R_prime: dict[tuple[int, int, str], int] = {
        (i, j, m): 0 for i in I for j in J for m in M
    }

    # Pre-compute lookup dicts from pandas Series
    apt_dict: dict[tuple[str, int], int] = {
        (str(m_), int(j_)): int(v)
        for (m_, j_), v in params.Apt.items()
    }
    t_travel_dict: dict[tuple[int, int, str, int], float] = {
        (int(i_), int(j_), str(m_), int(t_)): float(v)
        for (i_, j_, m_, t_), v in params.T_travel.items()
    }
    o_dict: dict[str, float] = {str(m_): float(v) for m_, v in params.O.items()}
    t_max = config.t_max_minutes

    # k -> p mapping
    k_to_p: dict[str, int] = config.priority_of_supply

    # Demand keys with D > 0 (only fire months)
    demand_index: set[tuple[int, str, int, int]] = {
        (int(j_), str(k_), int(t_), int(p_))
        for (j_, k_, t_, p_), v in params.D.items()
        if float(v) > 0.0 and int(t_) in T_dem
    }

    # Build trip_keys: (i,j,m,t,p) where apt=1 AND T+O <= T^max_p AND t in T_dem
    trip_set: set[tuple[int, int, str, int, int]] = set()
    for i in I:
        for j in J:
            for m in M:
                if apt_dict.get((m, j), 0) == 0:
                    continue
                for t in T_dem:
                    o_m = o_dict[m]
                    tt = t_travel_dict.get((i, j, m, t), 1e9)
                    for p in P:
                        if tt + o_m <= t_max[p]:
                            trip_set.add((i, j, m, t, p))

    trip_keys: gp.tuplelist = gp.tuplelist(sorted(trip_set))  # type: ignore[type-arg]

    # Build flow_keys: (i,j,k,m,t,p) where (i,j,m,t,p) feasible AND D_{jktp}>0
    flow_set: set[tuple[int, int, str, str, int, int]] = set()
    for (i, j, m, t, p) in trip_keys:
        for k in K:
            # only create x if there is demand for (j,k,t,p_k) -- p must match k's priority
            p_k = k_to_p[k]
            if (j, k, t, p_k) in demand_index and p == p_k:
                flow_set.add((i, j, k, m, t, p))

    flow_keys: gp.tuplelist = gp.tuplelist(sorted(flow_set))  # type: ignore[type-arg]

    # short_keys: (j,k,t,p) where D>0 and t in T_dem
    short_set: set[tuple[int, str, int, int]] = demand_index
    short_keys: gp.tuplelist = gp.tuplelist(sorted(short_set))  # type: ignore[type-arg]

    return Sets(
        I=I,
        J=J,
        K=K,
        M=M,
        T=T,
        P=P,
        Kv=Kv,
        Kn=Kn,
        T_dem=T_dem,
        Ig=Ig,
        R_prime=R_prime,
        flow_keys=flow_keys,
        trip_keys=trip_keys,
        short_keys=short_keys,
    )
