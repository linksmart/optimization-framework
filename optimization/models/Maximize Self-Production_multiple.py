from pyomo.core import *
import pyomo.environ
class Model:
	model = AbstractModel()
	
	model.N = Set()
	model.T = Set()  # Index Set for time steps of optimization horizon
	model.T_SoC = Set()  # SoC of the ESSs at the end of optimization horizon are also taken into account

	##################################       PARAMETERS            #################################
	################################################################################################

	model.dT = Param(within=PositiveIntegers)  # Number of seconds in one time step

	# model.Price_Forecast=Param(model.T)                             #Electric price forecast
	
	# definition of the energy storage system
	model.SoC_Value = Param(model.N, model.T_SoC, within=PositiveReals)
	model.ESS_Capacity = Param(model.N, within=PositiveReals)  # Storage Capacity of ESSs
	model.ESS_Max_Charge_Power = Param(model.N, within=PositiveReals)  # Max Charge Power of ESSs
	model.ESS_Max_Discharge_Power = Param(model.N, within=PositiveReals)  # Max Discharge Power of ESSs
	model.ESS_Charging_Eff = Param(model.N, within=PositiveReals)  # Charging efficiency of ESSs
	model.ESS_Discharging_Eff = Param(model.N, within=PositiveReals)  # Discharging efficiency of ESSs

	
	################################################################################################
	
	##################################       VARIABLES             #################################
	################################################################################################

	model.SoC_Copy = Var(model.N, model.T_SoC, within=PositiveReals)
	model.ESS_Capacity_Copy = Var(model.N, within=PositiveReals)
	################################################################################################

	###########################################################################
	#######                         CONSTRAINTS                         #######

	def con_rule_soc(model, n, t):
		return model.SoC_Copy[n, t] == model.SoC_Value[n, t]
	
	model.con_soc_copy = Constraint(model.N,  model.T_SoC, rule=con_rule_soc)

	def con_rule_ess(model, n):
		return model.ESS_Capacity_Copy[n] == model.ESS_Capacity[n]

	model.con_ess_copy = Constraint(model.N, rule=con_rule_ess)

	
	###########################################################################
	#######                         OBJECTIVE                           #######
	###########################################################################
	def obj_rule(model):
	    return 1
	
	model.obj = Objective(rule=obj_rule, sense=minimize)
