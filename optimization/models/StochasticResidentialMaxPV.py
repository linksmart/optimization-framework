from itertools import product

from pyomo.core import *


class Model:
    model = AbstractModel()

    # Feasible charge powers to ESS under the given conditions
    model.Feasible_ESS_Decisions = Set()

    # Feasible charge powers to VAC under the given conditions
    model.Feasible_VAC_Decisions = Set()

    model.Value_Index = Set(dimen=3)

    model.Value = Param(model.Value_Index, mutable=True)

    model.P_PV = Param(within=NonNegativeReals)

    model.Initial_ESS_SoC = Param(within=Reals, default=0)
    model.Initial_VAC_SoC = Param(within=Reals, default=0.0)

    model.Number_of_Parked_Cars = Param(within=PositiveIntegers)

    model.Unit_Consumption_Assumption = Param(within=PositiveReals)
    model.Unit_Drop_Penalty = Param(within=PositiveReals)
    model.ESS_Capacity = Param(within=PositiveReals)
    model.VAC_Capacity = Param(within=PositiveReals)

    model.Behavior_Model_Index = Set(dimen=2)
    model.Behavior_Model = Param(model.Behavior_Model_Index)

    model.dT = Param(within=PositiveIntegers)

    #######################################      Outputs       #######################################################

    # Combined decision
    model.Decision = Var(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions, within=Binary)

    model.P_ESS_OUTPUT = Var(within=Reals)
    model.P_VAC_OUTPUT = Var(within=NonNegativeReals)
    model.P_PV_OUTPUT = Var(bounds=(0, model.P_PV))
    model.P_GRID_OUTPUT = Var(within=Reals)

    def __init__(model, value, behaviorModel):
        model.Value = value
        model.behaviorModel = behaviorModel

    def combinatorics(model):
        # only one of the feasible decisions can be taken
        return 1 == sum(model.Decision[ess, vac] for ess, vac in
                        product(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions))

    model.const_integer = Constraint(rule=combinatorics)

    def ess_chargepower(model):
        return model.P_ESS_OUTPUT == sum(model.Decision[ess, vac] * ess for ess, vac in
                                         product(model.Feasible_ESS_Decisions,
                                                 model.Feasible_VAC_Decisions)) / 100 * model.ESS_Capacity / model.dT

    model.const_esschargepw = Constraint(rule=ess_chargepower)

    def vac_chargepower(model):
        return model.P_VAC_OUTPUT == sum(model.Decision[ess, vac] * vac for ess, vac in
                                         product(model.Feasible_ESS_Decisions,
                                                 model.Feasible_VAC_Decisions)) / 100 * model.VAC_Capacity / model.dT

    model.const_evchargepw = Constraint(rule=vac_chargepower)

    def home_demandmeeting(model):
        # Power demand must be met anyway
        return model.P_VAC_OUTPUT - model.P_ESS_OUTPUT == model.P_PV_OUTPUT + model.P_GRID_OUTPUT

    model.const_demand = Constraint(rule=home_demandmeeting)

    def objrule1(model):
        future_cost = 0

        # If vac is charged with one of the feasible decision 'p_ev'
        for p_ess, p_vac in product(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions):
            essSoC = p_ess + model.Initial_ESS_SoC  # Transition between ESS SOC states are always deterministic
            vacSoC = p_vac + model.Initial_VAC_SoC  # # Transition between EV SOC states are deterministic when the car is at home now

            valueOf_home = model.Value[(essSoC, vacSoC, 1)]
            valueOf_away = model.Value[(essSoC, vacSoC, 0)]

            # Expected future value= probability of swiching to home state*value of having home state
            #                       +probability of swiching to away state*value of having away state
            expected_future_cost_of_this_decision = model.Behavior_Model[(1, 1)] * valueOf_home + model.Behavior_Model[
                (1, 0)] * valueOf_away

            future_cost += model.Decision[
                               p_ess, p_vac] * expected_future_cost_of_this_decision  # Adding the expected_future cost of taking 'p_ess and p_ev' decision when initial condition is combination of 'ini_ess_soc','ini_ev_soc' and home state

        return model.P_PV - model.P_PV_OUTPUT + future_cost

    model.obj = Objective(rule=objrule1, sense=minimize)
