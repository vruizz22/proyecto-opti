from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from core.sets import Sets


@dataclass
class ModelVars:
    w: Any   # binary  (i,t)
    y: Any   # binary  (i,t)  — equivalent to R12b equality in model_builder
    s: Any   # continuous (i,k,t)
    c: Any   # continuous (i,k,t)
    x: Any   # continuous (i,j,k,m,t,p)  sparse
    n: Any   # integer   (i,j,m,t,p)     sparse
    e: Any   # integer   (i,t)
    f: Any   # continuous (j,k,t,p)       sparse


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
