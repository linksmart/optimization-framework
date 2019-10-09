from pyomo.core import *
from itertools import product


class Model:
    model = AbstractModel()

    model.T = Set()  # Index Set for time steps of optimization horizon
    # Feasible charge powers to ESS under the given conditions
    model.Feasible_ESS_Decisions = Set()

    # Feasible charge powers to VAC under the given conditions
    model.Feasible_VAC_Decisions = Set()



    model.Value_Index = Set(dimen=2)

    model.Value = Param(model.Value_Index, mutable=True)

    model.P_PV = Param(model.T, within=NonNegativeReals)  # PV PMPP forecast
    model.P_Load = Param(model.T, within=NonNegativeReals)

    model.Initial_ESS_SoC = Param(within=Reals, default=0)
    model.Initial_VAC_SoC = Param(within=Reals, default=0.0)

    model.Number_of_Parked_Cars = Param(within=PositiveIntegers)

    model.Unit_Consumption_Assumption = Param(within=PositiveReals)
    model.Unit_Drop_Penalty = Param(within=PositiveReals)
    model.ESS_Capacity = Param(within=PositiveReals)
    model.VAC_Capacity = Param(within=PositiveReals)

    model.Behavior_Model_Index = Set()
    model.Behavior_Model = Param(model.Behavior_Model_Index)


    model.dT = Param(within=PositiveIntegers)
    model.Timestep = Param(within=NonNegativeIntegers)

    #######################################      Outputs       #######################################################

    # Combined decision
    model.Decision = Var(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions, within=Binary)

    model.P_PV_single = Var(within=NonNegativeReals)
    model.P_Load_single = Var(within=NonNegativeReals)
    model.P_ESS_OUTPUT = Var(within=Reals) #change bounds
    model.P_VAC_OUTPUT = Var(within=NonNegativeReals) # change bounds
    model.P_PV_OUTPUT = Var(within=NonNegativeReals)
    model.P_GRID_OUTPUT = Var(within=Reals, initialize=0)
    #model.U = Var(within=Reals)

    def __init__(model, value, behaviorModel):
        model.Value = value
        model.behaviorModel = behaviorModel

    def combinatorics(model):
        # only one of the feasible decisions can be taken
        return 1 == sum(model.Decision[ess, vac] for ess, vac in
                        product(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions))

    model.const_integer = Constraint(rule=combinatorics)

    def rule_iniLoad(model):
        for j in model.P_Load:
            if j == model.Timestep:
                return model.P_Load_single == model.P_Load[j]

    model.con_IniLoad = Constraint(rule=rule_iniLoad)

    def rule_iniPV(model):
        for j in model.P_PV:
            if j == model.Timestep:
                return model.P_PV_single == model.P_PV[j]

    model.con_ess_IniPV = Constraint(rule=rule_iniPV)

    def con_rule_pv_potential(model):
        return model.P_PV_OUTPUT <= model.P_PV_single

    model.con_pv_pmax = Constraint(rule=con_rule_pv_potential)

    def ess_chargepower(model):
        return model.P_ESS_OUTPUT == sum(model.Decision[ess, vac] * ess for ess, vac in
                                         product(model.Feasible_ESS_Decisions,
                                                 model.Feasible_VAC_Decisions))  * (model.ESS_Capacity * 3600) / (100*model.dT)

    model.const_esschargepw = Constraint(rule=ess_chargepower)


    def vac_chargepower(model):
        return model.P_VAC_OUTPUT == sum(model.Decision[ess, vac] * vac for ess, vac in
                                         product(model.Feasible_ESS_Decisions,
                                                 model.Feasible_VAC_Decisions)) * (model.VAC_Capacity * 3600) / (100 * model.dT)

    model.const_evchargepw = Constraint(rule=vac_chargepower)

    def home_demandmeeting(model):
        # Power demand must be met anyway
        return model.P_VAC_OUTPUT + model.P_Load_single == model.P_ESS_OUTPUT + model.P_PV_OUTPUT + model.P_GRID_OUTPUT

    model.const_demand = Constraint(rule=home_demandmeeting)

    #def con_rule_linearization_1(model):
        #return model.U <= model.P_GRID_OUTPUT

    #model.con_linear_1 = Constraint(rule=con_rule_linearization_1)


    #def con_rule_linearization_2(model):
        #return model.U >= -model.P_GRID_OUTPUT

    #model.con_linear_2 = Constraint(rule=con_rule_linearization_2)


    def objrule1(model):
        future_cost = 0

        # If vac is charged with one of the feasible decision 'p_ev'
        for ess, vac in product(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions):

            essSoC = -ess + model.Initial_ESS_SoC  # Transition between ESS SOC states are always deterministic
            vacSoC = vac + model.Initial_VAC_SoC  # Transition between VAC SOC states are stochastic

            # Value of having fin_ess_soc and fin_vac_soc in next time interval
            expected_future_cost_of_this_decision = 0

            for p in range(model.Number_of_Parked_Cars + 1):
                # p: number of cars at park
                # d: number of cars driving
                d = model.Number_of_Parked_Cars - p

                final_vac_soc = vacSoC - d * model.Unit_Consumption_Assumption
                fin_vac_soc = final_vac_soc if final_vac_soc > 0 else 0

                penalty_for_negative_soc = -final_vac_soc / 100 * model.Unit_Drop_Penalty * (model.VAC_Capacity) if final_vac_soc < 0 else 0
                # Value of having fin_ess_soc,fin_ev_soc and home position in next time interval
                future_value_of_p_cars_at_Park = model.Value[(essSoC, fin_vac_soc)] + penalty_for_negative_soc
                # Probablity of p cars at home==Probability of d cars driving
                probability_of_p_cars_at_Park = model.Behavior_Model[p]

                expected_future_cost_of_this_decision += probability_of_p_cars_at_Park * future_value_of_p_cars_at_Park

            # Adding the expected_future cost of taking 'ess and vac' decision when initial condition is combination of 'ini_ess_soc' and 'ini_vac_soc'
            future_cost += model.Decision[ess, vac] * expected_future_cost_of_this_decision

        return model.P_GRID_OUTPUT * model.P_GRID_OUTPUT + future_cost

    model.obj = Objective(rule=objrule1, sense=minimize)
