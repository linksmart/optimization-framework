from pyomo.core import *
import pyomo.environ


class Model:
    model = AbstractModel()

    model.T = Set()  # Index Set for time steps of optimization horizon

    # definition of the load
    model.P_PV = Param(model.T, within=Reals)  # Active power demand

    ###########################################################################
    #######                         OBJECTIVE                           #######
    ###########################################################################
    def obj_rule(model):
        return 1

    model.obj = Objective(rule=obj_rule, sense=minimize)
