from pyomo.core import *
import pyomo.environ


class Model:
    model = AbstractModel()

    model.T = Set()  # Index Set for time steps of optimization horizon

    # definition of the load
    model.P_Load = Param(model.T, within=Reals)  # Active power demand


    model.Load_copy = Var(within=Reals)


    def con_rule_load(model):
        return model.Load_copy == model.P_Load[0] / 1000
    ###########################################################################
    #######                         OBJECTIVE                           #######
    ###########################################################################
    def obj_rule(model):
        return 1

    model.obj = Objective(rule=obj_rule, sense=minimize)
