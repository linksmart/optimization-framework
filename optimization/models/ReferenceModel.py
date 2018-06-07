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



    ###########################################################################
    #######                         CONSTRAINTS                         #######
    #######                Rule1: P_power demand meeting                #######
    #######                Rule2: Q_power demand meeting                #######
    #######                Rule3: State of charge consistency           #######
    #######                Rule4: Initial State of charge               #######
    #######                Rule5: ppv+j.qpv <= PB                       #######
    #######                Rule6: Voltage drop                          #######
    ###########################################################################
    def con_rule1(model,t):
        return model.P_Load_Forecast[t]==model.P_PV_Output[t]+ model.P_Grid_Output[t] + sum(model.P_ESS_Output[n,t] for n in model.N)
    def con_rule2(model,t):
        return model.Q_Load_Forecast[t]==model.Q_PV_Output[t]+ model.Q_Grid_Output[t]
    def con_rule3(model,n,t):
        return model.SoC_ESS[n,t+1]==model.SoC_ESS[n,t] - model.P_ESS_Output[n,t]*model.dT/model.ESS_Capacity[n]
    def con_rule4(model,n):
        return model.SoC_ESS[n,0]==model.ESS_SoC_Value[n]
    def con_rule5(model,t):
        return model.P_PV_Output[t]*model.P_PV_Output[t]+model.Q_PV_Output[t]*model.Q_PV_Output[t] <= model.P_PV_Forecast[t]*model.P_PV_Forecast[t]
    def con_rule6(model,t):
        return model.dV[t]==(model.Grid_R*model.P_Grid_Output[t]+model.Grid_X*model.Q_Grid_Output[t])/model.Grid_VGEN

    model.con1=Constraint(model.T,rule=con_rule1)
    model.con2=Constraint(model.T,rule=con_rule2)
    model.con3=Constraint(model.N,model.T,rule=con_rule3)
    model.con4=Constraint(model.N,rule=con_rule4)
    model.con5=Constraint(model.T,rule=con_rule5)
    model.con6=Constraint(model.T,rule=con_rule6)


    ###########################################################################
    #######                         OBJECTIVE                           #######
    ###########################################################################
    def obj_rule(model):
        if model.Target==1:   #Minimum exchange with grid
            return sum(model.P_Grid_Output[t]*model.P_Grid_Output[t]+model.Q_Grid_Output[t]*model.Q_Grid_Output[t] for t in model.T)
        #elif model.Target==2: #Maximum utilization of PV potential
            #return sum(model.P_PV_Forecast[m]-model.P_PV_Output[m] for t in model.T)
        #elif model.Target==3: #Minimum electricity bill
            #return sum(model.Price[t]*model.P_Grid_Output[t] for t in model.T)
        #elif model.Target==4: #Minimum voltage drop
            #return sum(model.dV[t]*model.dV[t] for t in model.T)
    model.obj=Objective(rule=obj_rule, sense = minimize)