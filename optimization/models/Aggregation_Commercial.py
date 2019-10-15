from pyomo.core import *
class Model:
	model = AbstractModel()

	##################################       PARAMETERS            #################################
	################################################################################################

	model.P_PV_50 = Param(within=NonNegativeReals)  # 10.8.0.38  EDYNA-0010
	model.P_PV_99 = Param(within=NonNegativeReals)  # 10.8.0.41	 EDYNA-0013
	model.ASM = Param(within=Reals)  # 10.8.0.40   EDYNA-0012
	model.Dummy_Chargers = Param(within=NonNegativeReals)  # 10.8.0.31   EDYNA-0003
	model.PCC = Param(within=Reals)  # 10.8.0.39	EDYNA-0011

	################################################################################################

	##################################       VARIABLES             #################################
	################################################################################################

	model.P_PV_Output = Var(within=NonNegativeReals, bounds=(0, 150))  # initialize=iniVal)
	model.Load = Var(within=NonNegativeReals)

	################################################################################################

	###########################################################################
	#######                         CONSTRAINTS                         #######

	# PV constraints
	def con_rule_pv_potential(model):
		return model.P_PV_Output == (model.P_PV_50 + model.P_PV_99) / 1000

	# Import/Export constraints
	def con_rule_load(model):
		return model.Load == (model.PCC - model.P_PV_99 + model.Dummy_Chargers) / 1000

	model.con_pv = Constraint(rule=con_rule_pv_potential)
	model.con_load = Constraint(rule=con_rule_load)

	###########################################################################
	#######                         OBJECTIVE                           #######
	###########################################################################
	def obj_rule(model):
		return model.Load

	model.obj = Objective(rule=obj_rule, sense=minimize)
