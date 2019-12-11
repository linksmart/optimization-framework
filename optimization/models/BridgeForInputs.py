from pyomo.core import *
import pyomo.environ


class Model:
	model = AbstractModel()
	##################################       PARAMETERS            #################################
	################################################################################################

	model.SoC_Value = Param(within=NonNegativeReals)
	# definition of the PV
	model.P_PV = Param(within=NonNegativeReals)  # PV PMPP forecast
	# definition of the load
	model.P_Load = Param(within=Reals)  # Active power demand
	model.P_Grid = Param(ithin=Reals)  # Active power demand
	model.P_EV = Param(within=NonNegativeReals)

	################################################################################################

	##################################       VARIABLES             #################################
	################################################################################################

	model.SoC_copy = Var(within=NonNegativeReals)
	model.PV_copy = Var(within=NonNegativeReals)
	model.Load_copy = Var(within=Reals)
	model.Grid_copy = Var(within=Reals)
	model.EV_copy = Var(within=NonNegativeReals)

	################################################################################################

	###########################################################################
	#######                         CONSTRAINTS                         #######

	def con_rule_soc(model):
		return model.SoC_copy == model.SoC_Value

	def con_rule_pv(model):
		return model.PV_copy == model.P_PV / 1000

	def con_rule_load(model):
		return model.Load_copy == model.P_Load/1000

	def con_rule_grid(model):
		return model.Grid_copy == model.P_Grid/1000

	def con_rule_ev(model):
		return model.EV_copy == model.P_EV/ 1000

	model.con_soc = Constraint(rule=con_rule_soc)
	model.con_pv = Constraint(rule=con_rule_pv)
	model.con_load = Constraint(rule=con_rule_load)
	model.con_grid = Constraint(rule=con_rule_grid)
	model.con_ev = Constraint(rule=con_rule_ev)

	###########################################################################
	#######                         OBJECTIVE                           #######
	###########################################################################
	def obj_rule(model):
		return 1

	model.obj = Objective(rule=obj_rule, sense=minimize)
