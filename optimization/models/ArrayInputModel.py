from pyomo.core import *

class Model:

    model = AbstractModel()

    model.T = Set()  # Index Set for time steps of optimization horizon
    model.S = Set()  # Index Set for time steps of optimization horizon

    ##################################       PARAMETERS            #################################
    ################################################################################################

    # definition of the PV
    model.P_PV = Param(model.S, model.T, within=NonNegativeReals)  # PV PMPP forecast
    model.P_Load = Param(model.T, within=NonNegativeReals)