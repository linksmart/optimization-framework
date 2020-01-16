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

    model.Value = Param(model.Value_Index, within=Reals)

    model.P_PV = Param(model.T, within=NonNegativeReals)  # PV PMPP forecast
    model.PV_Inv_Max_Power = Param(within=PositiveReals)  # PV inverter capacity
    model.P_Load = Param(model.T, within=NonNegativeReals)

    model.Initial_ESS_SoC = Param(within=Reals, default=0.0)
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
    model.Max_Charging_Power_kW = Param(within=NonNegativeReals)


    model.P_Grid_Max_Export_Power = Param(within=NonNegativeReals)  # Max active power export

    model.ESS_Max_Charge_Power = Param(within=PositiveReals)  # Max Charge Power of ESSs
    model.ESS_Max_Discharge_Power = Param(within=PositiveReals)  # Max Discharge Power of ESSs

    #######################################      Outputs       #######################################################

    # Combined decision
    model.Decision = Var(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions, within=Binary,initialize=0)

    model.P_ESS_OUTPUT = Var(within=Reals, bounds=(-model.ESS_Max_Charge_Power, model.ESS_Max_Discharge_Power))
    model.P_VAC_OUTPUT = Var(within=NonNegativeReals, bounds=(0, model.Max_Charging_Power_kW))
    model.P_PV_OUTPUT = Var(within=NonNegativeReals, bounds=(0, model.PV_Inv_Max_Power))
    model.P_GRID_OUTPUT = Var(within=Reals,bounds=(-model.P_Grid_Max_Export_Power, model.P_Grid_Max_Export_Power))

    model.P_PV_single = Var(within=NonNegativeReals, bounds=(0, model.PV_Inv_Max_Power))
    model.P_Load_single = Var(within=NonNegativeReals)

    model.future_cost = Var(within=Reals)
    model.expected_future_cost = Var(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions, within=Reals,initialize=0.0)


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
                return model.P_PV_single == model.P_PV[j]/1000

    model.con_ess_IniPV = Constraint(rule=rule_iniPV)

    def con_rule_pv_potential(model):
        return model.P_PV_OUTPUT == model.P_PV_single

    model.con_pv_pmax = Constraint(rule=con_rule_pv_potential)

    def ess_chargepower(model):
        return model.P_ESS_OUTPUT == sum(model.Decision[ess, vac] * ess for ess, vac in
                                         product(model.Feasible_ESS_Decisions,
                                                 model.Feasible_VAC_Decisions)) * (model.ESS_Capacity * 3600) / (100*model.dT)

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

    def con_expected_future_value(model, p_ess, p_vac):
        essSoC = -p_ess + model.Initial_ESS_SoC  # Transition between ESS SOC states are always deterministic
        vacSoC = p_vac + model.Initial_VAC_SoC  # Transition between EV SOC states are deterministic when the car is at home now
        expected_future_cost_per_number_cars = 0
        for p in range(model.Number_of_Parked_Cars + 1):
            # p: number of cars at park
            # d: number of cars driving
            d = model.Number_of_Parked_Cars - p

            final_vac_soc = vacSoC - d * model.Unit_Consumption_Assumption
            fin_vac_soc = final_vac_soc if final_vac_soc > 0 else 0

            penalty_for_negative_soc = -final_vac_soc / 100 * model.Unit_Drop_Penalty * (
                model.VAC_Capacity) if final_vac_soc < 0 else 0
            # Value of having fin_ess_soc,fin_ev_soc and home position in next time interval
            future_value_of_p_cars_at_Park = model.Value[(essSoC, fin_vac_soc)] + penalty_for_negative_soc
            # Probablity of p cars at home==Probability of d cars driving
            probability_of_p_cars_at_Park = model.Behavior_Model[p]
            expected_future_cost_per_number_cars += future_value_of_p_cars_at_Park * probability_of_p_cars_at_Park

        return model.expected_future_cost[p_ess,p_vac] == expected_future_cost_per_number_cars

    model.rule_expected_future_value = Constraint(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions,rule=con_expected_future_value)

    def con_future_cost(model):
        return model.future_cost == sum(model.Decision[p_ess, p_vac] * model.expected_future_cost[p_ess, p_vac]
                                        for p_ess, p_vac in
                                        product(model.Feasible_ESS_Decisions, model.Feasible_VAC_Decisions))
    model.rule_future_cost = Constraint(rule=con_future_cost)

    def objrule1(model):

            return model.P_GRID_OUTPUT * model.P_GRID_OUTPUT + model.future_cost

    model.obj = Objective(rule=objrule1, sense=minimize)

