# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 14:08:34 2018

@author: guemruekcue
"""

from pyomo.core import *

class Model:
    #
    # Model
    #

    model = AbstractModel()

    #
    # Parameters
    #

    model.I = Set()  # Raw materials
    model.J = Set()  # Product types
    model.T = Set()  # Time periods

    model.c = Param(model.I, within=NonNegativeReals)  # c[i]  : Present cost of raw material i
    model.a = Param(model.I, model.J, within=PositiveReals)  # a[i,j]: Raw material i required per unit of product j
    model.f = Param(model.J, model.T, within=PositiveReals)  # f[j,t]: Cost of outsourcing product j in time period t
    model.b = Param(within=PositiveReals)  # b     : Inventory capacity

    model.d = Param(model.J, model.T, within=NonNegativeReals)  # d[j,t]: Random demand of product j in time period t

    #
    # Variables
    #
    model.x = Var(model.I, model.T,
              within=NonNegativeReals)  # First stage variables:  x[i,t]: Quantity of raw material i purchased for use in period t
    model.y = Var(model.J, model.T,
              within=NonNegativeReals)  # Second stage variables: y[j,t]: Quantity of product j outsourced in period t

    model.FirstStageCost = Var(within=NonNegativeReals)
    model.LaterStageCost = Var(model.T, within=NonNegativeReals)


    #
    # Constraints
    #
    def inventory_capacity(model):
        return summation(model.x) <= model.b


    model.InventoryCapacityConstraint = Constraint(rule=inventory_capacity)


    def demand_meeting(model, j, t):
        return (sum([model.a[i, j] * model.x[i, t] + model.y[j, t] for i in model.I]) - model.d[j, t]) >= 0


    model.DemandConstraint = Constraint(model.J, model.T, rule=demand_meeting)


    def first_stage_cost(model):
        return model.FirstStageCost == sum([model.c[i] * model.x[i, t] for i in model.I for t in model.T])


    model.FirstStageCostConstraint = Constraint(rule=first_stage_cost)


    def later_stage_cost(model, t):
        return model.LaterStageCost[t] == sum([model.f[j, t] * model.y[j, t] for j in model.J])


    model.LaterStageCostConstraint = Constraint(model.T, rule=later_stage_cost)


    ## Objective
    #
    def objective_rule(model):
        return model.FirstStageCost + summation(model.LaterStageCost)


    model.Obj = Objective(rule=objective_rule)