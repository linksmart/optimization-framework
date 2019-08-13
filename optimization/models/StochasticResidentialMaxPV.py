from itertools import product

from pyomo.core import *


class Model:
    model = AbstractModel()

    model.T = Set()  # Index Set for time steps of optimization horizon
    # Feasible charge powers to ESS under the given conditions
    model.Feasible_ESS_Decisions = Set()

    # Feasible charge powers to VAC under the given conditions
    model.Feasible_VAC_Decisions = Set()

    model.Value_Index = Set(dimen=3)

    model.Value = Param(model.Value_Index, mutable=True)

    model.P_PV = Param(model.T, within=NonNegativeReals)  # PV PMPP forecast

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
    model.Recharge = Param(within=Binary)
    model.VAC_States_Min = Param(within=NonNegativeReals) #it should accept 0
    model.Timestep = Param(within=NonNegativeIntegers)

    #######################################      Outputs       #######################################################

    # Combined decision
    if model.Recharge == 1:
        model.Decision_with_EV = Var(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions, within=Binary)
    else:
        model.Decision_without_EV = Var(model.Feasible_ESS_Decisions, within=Binary)

    model.P_ESS_OUTPUT = Var(within=Reals)
    model.P_VAC_OUTPUT = Var(within=NonNegativeReals)
    model.P_PV_OUTPUT = Var(within=NonNegativeReals)
    model.P_GRID_OUTPUT = Var(within=Reals)
    model.P_PV_single = Var(within=NonNegativeReals)

    def __init__(model, value, behaviorModel):
        model.Value = value
        model.behaviorModel = behaviorModel

    def combinatorics(model):
        # only one of the feasible decisions can be taken
        if model.Recharge == 1:
            return 1 == sum(model.Decision_with_EV[ess, vac] for ess, vac in
                            product(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions))
        else:
            return 1 == sum(model.Decision_without_EV[ess] for ess in model.Feasible_ESS_Decisions)

    model.const_integer = Constraint(rule=combinatorics)

    def rule_iniPV(model):
        for j in model.P_PV:
            if j == model.Timestep:
                return model.P_PV_single == model.P_PV[j]

    model.con_ess_IniPV = Constraint(rule=rule_iniPV)

    def con_rule_pv_potential(model):
        return model.P_PV_OUTPUT <= model.P_PV_single

    model.con_pv_pmax = Constraint(rule=con_rule_pv_potential)

    def ess_chargepower(model):
        if model.Recharge == 1:
            return model.P_ESS_OUTPUT == sum(model.Decision_with_EV[ess, vac] * ess for ess, vac in
                                             product(model.Feasible_ESS_Decisions,
                                                     model.Feasible_VAC_Decisions)) * (model.ESS_Capacity * 3600) / (100 * model.dT)
        else:
            return model.P_ESS_OUTPUT == sum(model.Decision_without_EV[ess] * ess for ess in (model.Feasible_ESS_Decisions) * (model.ESS_Capacity * 3600) / (100 * model.dT))

    model.const_esschargepw = Constraint(rule=ess_chargepower)

    def vac_chargepower(model):
        if model.Recharge == 1:
            return model.P_VAC_OUTPUT == sum(model.Decision_with_EV[ess, vac] * vac for ess, vac in
                                             product(model.Feasible_ESS_Decisions,
                                                     model.Feasible_VAC_Decisions)) * (model.VAC_Capacity * 3600) / (
                               100 * model.dT)
        else:
            return model.P_VAC_OUTPUT == 0

    model.const_evchargepw = Constraint(rule=vac_chargepower)

    def home_demandmeeting(model):
        # Power demand must be met anyway
        return model.P_VAC_OUTPUT == model.P_ESS_OUTPUT + model.P_PV_OUTPUT + model.P_GRID_OUTPUT

    model.const_demand = Constraint(rule=home_demandmeeting)

    def objrule1(model):

        future_cost = 0
        if model.Recharge == 1:
            # If vac is charged with one of the feasible decision 'p_ev'
            for p_ess, p_vac in product(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions):
                essSoC = -p_ess + model.Initial_ESS_SoC  # Transition between ESS SOC states are always deterministic
                vacSoC = p_vac + model.Initial_VAC_SoC  # # Transition between EV SOC states are deterministic when the car is at home now

                valueOf_home = model.Value[(essSoC, vacSoC, 1)]
                valueOf_away = model.Value[(essSoC, vacSoC, 0)]

                # Expected future value= probability of swiching to home state*value of having home state
                #                       +probability of swiching to away state*value of having away state
                expected_future_cost_of_this_decision = model.Behavior_Model[(1, 1)] * valueOf_home + model.Behavior_Model[
                    (1, 0)] * valueOf_away

                future_cost += model.Decision_with_EV[
                                   p_ess, p_vac] * expected_future_cost_of_this_decision  # Adding the expected_future cost of taking 'p_ess and p_ev' decision when initial condition is combination of 'ini_ess_soc','ini_ev_soc' and home state

            return model.P_PV_single - model.P_PV_OUTPUT + future_cost
        else:
            # The car reaches to 'final_ev' by driving during one time interval
            final_ev_soc = model.Initial_VAC_SoC - model.Unit_Consumption_Assumption
            # The case after dropping below ev_minSoC will be considered as if they dropped to ev_minSoC%
            vacSoC = final_ev_soc if final_ev_soc >= model.VAC_States_Min else model.VAC_States_Min

            for p_ess in model.Feasible_ESS_Decisions:
                essSoC = -p_ess + model.Initial_ESS_SoC  # Transition between ESS SOC states are always deterministic

                # Extra penalty for dropping below predefined ev_minSoC limit
                penalty_for_negative_soc_home = (model.VAC_States_Min - final_ev_soc) / 100 * model.Unit_Drop_Penalty * model.VAC_Capacity if final_ev_soc < model.VAC_States_Min else 0
                #penalty_for_negative_soc_away = (model.VAC_States_Min - final_ev_soc) / 100 * model.Unit_Drop_Penalty * model.VAC_Capacity if final_ev_soc < model.VAC_States_Min else 0
                penalty_for_negative_soc_away = penalty_for_negative_soc_home

                valueOf_home = model.Value[(essSoC, vacSoC, 1)]+penalty_for_negative_soc_home    #Value of having fin_ess_soc,fin_ev_soc and home position in next time interval
                valueOf_away = model.Value[(essSoC, vacSoC, 0)]+penalty_for_negative_soc_away    #Value of having fin_ess_soc,fin_ev_soc and away position in next time interval

                # Expected future value= probability of swiching to home state*value of having home state
                #                       +probability of swiching to away state*value of having away state
                expected_future_cost_of_this_decision = model.Behavior_Model[(0, 1)] * valueOf_home + model.Behavior_Model[
                    (0, 0)] * valueOf_away

                future_cost += model.Decision_without_EV[
                                   p_ess] * expected_future_cost_of_this_decision  # Adding the expected_future cost of taking 'p_ess and p_ev' decision when initial condition is combination of 'ini_ess_soc','ini_ev_soc' and home state

            return model.P_PV_single - model.P_PV_OUTPUT + future_cost


    model.obj = Objective(rule=objrule1, sense=minimize)
