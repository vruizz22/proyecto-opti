from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from core.sets import Sets


@dataclass
class ModelVars:
    # w_{it} ∈ {0,1}: 1 si la bodega i se habilita/abre en el período t.
    # Garantiza el pago del costo fijo F_i una única vez (R12a: sum_t w_{it} ≤
    # 1).
    w: Any

    # y_{it} ∈ {0,1}: 1 si la bodega i está operativa en el período t.
    # Determinado por R12b: y_{it} = sum_{τ≤t} w_{iτ}.
    # Una bodega abierta en τ permanece activa el resto del horizonte.
    y: Any

    # s_{ikt} ≥ 0: stock del insumo k en la bodega i al final del período t [unidades].
    # Balance R2 (no perecibles): s_{ikt} = s_{ik,t-1} + c_{ikt} - despachos.
    # R3 fuerza s_{ikt} = 0 para perecibles (K_v).
    s: Any

    # c_{ikt} ≥ 0: compras del insumo k para la bodega i en el período t [unidades].
    # Condicionado a apertura por R14 (big-M = C_i / E_k).
    c: Any

    # x_{ijkmtp} ≥ 0: unidades del insumo k enviadas desde la bodega i a la
    # comuna j, usando vehículo m, en período t, con prioridad p.
    # Solo existe para (i,j,k,m,t,p) ∈ flow_keys (Apt=1, T_{ijm}+O_m ≤
    # T^max_p, D>0).
    x: Any

    # n_{ijmtp} ∈ Z≥0: número de viajes del vehículo m asignados a la ruta
    # bodega-i → comuna-j en período t, prioridad p.
    # Solo existe para (i,j,m,t,p) ∈ trip_keys (factibilidad temporal ya
    # filtrada).
    n: Any

    # e_{it} ∈ Z≥0: dotación de personal en la bodega i durante el período t [personas].
    # Acotada por R10a (piso L_i·y_{it}) y R10b (techo E^max_i·y_{it}).
    e: Any

    # f_{jktp} ≥ 0: demanda no cubierta (faltante) del insumo k en la comuna j,
    # período t, prioridad p [unidades].  Penalizada con π_p en la función
    # objetivo.
    f: Any


def create_vars(model: gp.Model, sets: Sets) -> ModelVars:
    I, K, T = sets.I, sets.K, sets.T

    it_keys = gp.tuplelist([(i, t) for i in I for t in T])
    ikt_keys = gp.tuplelist([(i, k, t) for i in I for k in K for t in T])

    w = model.addVars(it_keys, vtype=GRB.BINARY, name="w")
    y = model.addVars(it_keys, vtype=GRB.BINARY, name="y")
    s = model.addVars(ikt_keys, lb=0.0, name="s")
    c = model.addVars(ikt_keys, lb=0.0, name="c")
    x = model.addVars(sets.flow_keys, lb=0.0, name="x")
    n = model.addVars(sets.trip_keys, lb=0, vtype=GRB.INTEGER, name="n")
    e = model.addVars(it_keys, lb=0, vtype=GRB.INTEGER, name="e")
    f = model.addVars(sets.short_keys, lb=0.0, name="f")

    return ModelVars(w=w, y=y, s=s, c=c, x=x, n=n, e=e, f=f)
