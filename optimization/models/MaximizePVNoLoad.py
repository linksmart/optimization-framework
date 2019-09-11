from pyomo.core import *
class Model:
	model = AbstractModel()
	
	
	model.T = Set()  # Index Set for time steps of optimization horizon
	model.T_SoC = Set()  # SoC of the ESSs at the end of optimization horizon are also taken into account
	
	##################################       PARAMETERS            #################################
	################################################################################################
	
	model.dT = Param(within=PositiveIntegers)  # Number of seconds in one time step
	
	# model.Price_Forecast=Param(model.T)                             #Electric price forecast
	model.P_PV = Param(model.T, within=NonNegativeReals)  # PV PMPP forecast
	
	model.ESS_Min_SoC = Param(within=PositiveReals)  # Minimum SoC of ESSs
	model.ESS_Max_SoC = Param(within=PositiveReals)  # Maximum SoC of ESSs
	model.SoC_Value = Param(within=PositiveReals)
	model.ESS_Capacity = Param(within=PositiveReals)  # Storage Capacity of ESSs
	model.ESS_Max_Charge_Power = Param(within=PositiveReals)  # Max Charge Power of ESSs
	model.ESS_Max_Discharge_Power = Param(within=PositiveReals)  # Max Discharge Power of ESSs
	model.ESS_Charging_Eff = Param(within=PositiveReals)  # Charging efficiency of ESSs
	model.ESS_Discharging_Eff = Param(within=PositiveReals)  # Discharging efficiency of ESSs
	
	model.P_Grid_Max_Export_Power = Param(within=NonNegativeReals)  # Max active power export
	model.Q_Grid_Max_Export_Power = Param(within=NonNegativeReals)  # Max reactive power export
	
	model.PV_Inv_Max_Power = Param(within=PositiveReals)  # PV inverter capacity
	################################################################################################
	
	##################################       VARIABLES             #################################
	################################################################################################
	
	model.P_Grid_R_Output = Var(model.T, within=Reals)  # Active power exchange with grid at R phase
	model.P_Grid_S_Output = Var(model.T, within=Reals)  # Active power exchange with grid at S phase
	model.P_Grid_T_Output = Var(model.T, within=Reals)  # Active power exchange with grid at S phase
	model.P_Grid_Output = Var(model.T, within=Reals)
	model.Q_Grid_R_Output = Var(model.T, within=Reals)  # Reactive power exchange with grid at R phase
	model.Q_Grid_S_Output = Var(model.T, within=Reals)  # Reactive power exchange with grid at S phase
	model.Q_Grid_T_Output = Var(model.T, within=Reals)  # Reactive power exchange with grid at T phase
	model.Q_Grid_Output = Var(model.T, within=Reals)
	
	model.P_PV_Output = Var(model.T, within=NonNegativeReals, bounds=(0, model.PV_Inv_Max_Power))  # initialize=iniVal)
	model.P_ESS_Output = Var(model.T, within=Reals, bounds=(
	    -model.ESS_Max_Charge_Power, model.ESS_Max_Discharge_Power))  # ,initialize=iniSoC)
	model.SoC_ESS = Var(model.T_SoC, within=NonNegativeReals, bounds=(model.ESS_Min_SoC, model.ESS_Max_SoC))
	
	################################################################################################
	
	###########################################################################
	#######                         CONSTRAINTS                         #######
	
	# PV constraints
	def con_rule_pv_potential(model, t):
	    return model.P_PV_Output[t] <= model.P_PV[t]
	
	# Import/Export constraints
	def con_rule_grid_P(model, t):
	    return model.P_Grid_Output[t] == model.P_Grid_R_Output[t] + model.P_Grid_S_Output[t] + model.P_Grid_T_Output[t]
	
	def con_rule_grid_P_inv(model, t):
	    return model.P_Grid_Output[t] >= -model.P_Grid_Max_Export_Power
	
	def con_rule_grid_Q(model, t):
	    return model.Q_Grid_Output[t] == model.Q_Grid_R_Output[t] + model.Q_Grid_S_Output[t] + model.Q_Grid_T_Output[t]
	
	def con_rule_grid_Q_inv(model, t):
	    return model.Q_Grid_Output[t] >= -model.Q_Grid_Max_Export_Power
	
	# ESS SoC balance
	def con_rule_socBalance(model, t):
	    return model.SoC_ESS[t + 1] == model.SoC_ESS[t] - model.P_ESS_Output[t] * model.dT / model.ESS_Capacity / 3600

	def con_rule_iniSoC(model):
		soc = model.SoC_Value / 100
		soc_return = 0
		if soc >= model.ESS_Max_SoC:
			soc_return = model.ESS_Max_SoC
		elif soc <= model.ESS_Min_SoC:
			soc_return = model.ESS_Min_SoC
		else:
			soc_return = soc
		return model.SoC_ESS[0] == soc_return

	
	# Generation-feed in balance
	def con_rule_generation_feedin(model, t):
	    return model.P_Grid_Output[t] * model.P_Grid_Output[t] + model.Q_Grid_Output[t] * model.Q_Grid_Output[t] == (
	            model.P_PV_Output[t] + model.P_ESS_Output[t]) * (model.P_PV_Output[t] + model.P_ESS_Output[t])
	
	model.con_pv_pmax = Constraint(model.T, rule=con_rule_pv_potential)
	
	model.con_grid_P = Constraint(model.T, rule=con_rule_grid_P)
	model.con_grid_inv_P = Constraint(model.T, rule=con_rule_grid_P_inv)
	model.con_grid_Q = Constraint(model.T, rule=con_rule_grid_Q)
	model.con_grid_inv_Q = Constraint(model.T, rule=con_rule_grid_Q_inv)
	
	model.con_ess_soc = Constraint(model.T, rule=con_rule_socBalance)
	model.con_ess_Inisoc = Constraint(rule=con_rule_iniSoC)
	
	model.con_gen_feedin = Constraint(model.T, rule=con_rule_generation_feedin)
	
	###########################################################################
	#######                         OBJECTIVE                           #######
	###########################################################################
	def obj_rule(model):
	    return sum(model.P_PV[t] - model.P_PV_Output[t] for t in model.T)
	
	model.obj = Objective(rule=obj_rule, sense=minimize)
