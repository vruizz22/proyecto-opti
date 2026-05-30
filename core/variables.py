from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import gurobipy as gp
from gurobipy import GRB


@dataclass
class ModelVars:
    # w_{it}: 1 si bodega i se abre en t
    w: Any  # dict[(i,t), Var]
    # y_{it}: 1 si bodega i está operativa en t
    y: Any  # dict[(i,t), Var]
    # s_{ikt}: inventario al final de periodo t
    s: Any  # dict[(i,k,t), Var]
    # c_{ikt}: compras en periodo t
    c: Any  # dict[(i,k,t), Var]
    # x_{ijkmtp}: flujo de insumo k
    x: Any  # dict[(i,j,k,m,t,p), Var]
    # n_{ijmtp}: viajes asignados
    n: Any  # dict[(i,j,m,t,p), Var]
    # e_{it}: dotación personal
    e: Any  # dict[(i,t), Var]
    # f_{jktp}: faltante
    f: Any  # dict[(j,k,t,p), Var]


def create_vars(
    model: gp.Model,
    sets_obj: "Sets",  # type: ignore[name-defined]  # noqa: F821
) -> ModelVars:
    from core.sets import Sets
    s: Sets = sets_obj

    I, K, T = s.I, s.K, s.T

    it_keys = gp.tuplelist([(i, t) for i in I for t in T])
    ikt_keys = gp.tuplelist([(i, k, t) for i in I for k in K for t in T])

    w = model.addVars(it_keys, vtype=GRB.BINARY, name="w")
    y = model.addVars(it_keys, vtype=GRB.BINARY, name="y")
    s_var = model.addVars(ikt_keys, lb=0.0, name="s")
    c_var = model.addVars(ikt_keys, lb=0.0, name="c")
    x_var = model.addVars(s.flow_keys, lb=0.0, name="x")
    n_var = model.addVars(s.trip_keys, lb=0, vtype=GRB.INTEGER, name="n")
    e_var = model.addVars(it_keys, lb=0, vtype=GRB.INTEGER, name="e")
    f_var = model.addVars(s.short_keys, lb=0.0, name="f")

    return ModelVars(
        w=w,
        y=y,
        s=s_var,
        c=c_var,
        x=x_var,
        n=n_var,
        e=e_var,
        f=f_var,
    )
