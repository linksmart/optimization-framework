from pyomo.core import *
import pyomo.environ
class Model:
	model = AbstractModel()
	
	
	model.T = Set()  # Index Set for time steps of optimization horizon
	model.T_SoC = Set()  # SoC of the ESSs at the end of optimization horizon are also taken into account
	
	##################################       PARAMETERS            #################################
	################################################################################################
	
	model.dT = Param(within=PositiveIntegers)  # Number of seconds in one time step
	
	# model.Price_Forecast=Param(model.T)                             #Electric price forecast
	
	# definition of the energy storage system
	model.ESS_Min_SoC = Param(within=NonNegativeReals)  # Minimum SoC of ESSs
	model.ESS_Max_SoC = Param(within=PositiveReals)  # Maximum SoC of ESSs
	model.SoC_Value = Param(within=NonNegativeReals)
	model.ESS_Capacity = Param(within=PositiveReals)  # Storage Capacity of ESSs
	model.ESS_Max_Charge_Power = Param(within=PositiveReals)  # Max Charge Power of ESSs
	model.ESS_Max_Discharge_Power = Param(within=PositiveReals)  # Max Discharge Power of ESSs
	model.ESS_Charging_Eff = Param(within=PositiveReals)  # Charging efficiency of ESSs
	model.ESS_Discharging_Eff = Param(within=PositiveReals)  # Discharging efficiency of ESSs

	model.Fronius_Max_Power = Param(within=PositiveReals)

	#definition of the grid maximal power
	model.P_Grid_Max_Export_Power = Param(within=NonNegativeReals)  # Max active power export
	model.Q_Grid_Max_Export_Power = Param(within=NonNegativeReals)  # Max reactive power export
	
	#definition of the PV
	model.P_PV = Param(model.T, within=NonNegativeReals)  # PV PMPP forecast
	model.PV_Inv_Max_Power = Param(within=PositiveReals)  # PV inverter capacity
	
	#definition of the load
	model.P_Load = Param(model.T, within=Reals)  # Active power demand
	
	
	################################################################################################
	
	##################################       VARIABLES             #################################
	################################################################################################

	model.P_Grid_Output = Var(model.T, within=Reals,
							  bounds=(-model.P_Grid_Max_Export_Power, model.P_Grid_Max_Export_Power))
	model.P_PV_Output = Var(model.T, within=NonNegativeReals, bounds=(0, model.PV_Inv_Max_Power))  # initialize=iniVal)
	model.P_ESS_Output = Var(model.T, within=Reals,
							 bounds=(-model.ESS_Max_Charge_Power, model.ESS_Max_Discharge_Power),
							 initialize=0)  # ,initialize=iniSoC)
	model.P_ESS_Output_Pct = Var(model.T, within=Reals, initialize=0)
	model.SoC_ESS = Var(model.T_SoC, within=NonNegativeReals, bounds=(model.ESS_Min_SoC, model.ESS_Max_SoC))
	model.P_Fronius = Var(model.T, within=Reals, bounds=(-model.Fronius_Max_Power, model.Fronius_Max_Power),
						  initialize=0)
	model.P_Fronius_Pct = Var(model.T, within=Reals, initialize=0)
	model.P_Fronius_Pct_Output = Var(model.T, within=Reals, initialize=0)
	model.U = Var(model.T, within=Reals)

	model.SoC_copy = Var(within=NonNegativeReals)
	model.PV_copy = Var(within=NonNegativeReals)
	model.Load_copy = Var(within=Reals)

	################################################################################################

	###########################################################################
	#######                         CONSTRAINTS                         #######

	# rule to limit the PV ouput to value of the PV forecast
	def con_rule_pv_potential(model, t):
		return model.P_PV_Output[t] <= model.P_PV[t] / 1000

	def con_rule_fronius_power(model, t):
		return model.P_PV_Output[t] + model.P_ESS_Output[t] == model.P_Fronius[t]

	# ESS SoC balance
	def con_rule_socBalance(model, t):
		return model.SoC_ESS[t + 1] == model.SoC_ESS[t] - model.P_ESS_Output[t] * model.dT / model.ESS_Capacity / 3600

	# initialization of the first SoC value to the value entered through the API
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

	# Definition of the energy balance in the system
	def con_rule_energy_balance(model, t):
		return model.P_Load[t] / 1000 == model.P_Fronius[t] + model.P_Grid_Output[t]

	def con_rule_output_ess_power_pct(model, t):
		return model.P_ESS_Output_Pct[t] == (100 / model.ESS_Max_Charge_Power) * model.P_ESS_Output[t]

	def con_rule_output_ess_power(model, t):
		return model.P_Fronius_Pct[t] == (100 / model.Fronius_Max_Power) * model.P_Fronius[t]

	def con_rule_is_positive(model, t):
		return model.P_Fronius_Pct[t] >= 0

	def con_rule_limiting_pct(model, t):
		return model.is_positive[t] * model.P_Fronius_Pct[t] == model.P_Fronius_Pct_Output[t]

	def con_rule_soc(model):
		return model.SoC_copy == model.SoC_Value

	def con_rule_pv(model):
		return model.PV_copy == model.P_PV[0] / 1000

	def con_rule_load(model):
		return model.Load_copy == model.P_Load[0] / 1000

	def con_rule_linearization_1(model, t):
		return model.U[t] <= model.P_Grid_Output[t]

	def con_rule_linearization_2(model, t):
		return model.U[t] >= -model.P_Grid_Output[t]

	model.con_pv_max = Constraint(model.T, rule=con_rule_pv_potential)
	model.con_fronius_power = Constraint(model.T, rule=con_rule_fronius_power)
	model.con_ess_soc = Constraint(model.T, rule=con_rule_socBalance)
	model.con_ess_Inisoc = Constraint(rule=con_rule_iniSoC)
	model.con_energy_balance = Constraint(model.T, rule=con_rule_energy_balance)
	model.con_ess_percentage = Constraint(model.T, rule=con_rule_output_ess_power_pct)
	model.con_percentage = Constraint(model.T, rule=con_rule_output_ess_power)
	model.is_positive = Expression(model.T, rule=con_rule_is_positive)
	model.con_limiting_pct = Constraint(model.T, rule=con_rule_limiting_pct)
	model.con_linear_1 = Constraint(model.T, rule=con_rule_linearization_1)
	model.con_linear_2 = Constraint(model.T, rule=con_rule_linearization_2)

	model.con_soc = Constraint(rule=con_rule_soc)
	model.con_pv = Constraint(rule=con_rule_pv)
	model.con_load = Constraint(rule=con_rule_load)

	###########################################################################
	#######                         OBJECTIVE                           #######
	###########################################################################
	def obj_rule(model):
	    return sum(model.U[t] for t in model.T)
	
	model.obj = Objective(rule=obj_rule, sense=minimize)
