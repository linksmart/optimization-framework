from pyomo.core import *


class Model:

	def calculate_expectation(self, ts, essSoC, vacSoC, park, unitConsumptionAssumption, unitDropPenalty, VAC_Capacity, Value, behaviorModel):
		"""
		Calculates expected_future_cost of the decision that charges vac to vacSoC
		"""

		expected_future_cost = 0

		# self.park.carNb == Number of cars

		for p in range(park.carNb+1):
			# p: number of cars at park
			# d: number of cars driving
			d = park.carNb-p

			final_vac_soc = vacSoC - d * unitConsumptionAssumption
			fin_vac_soc = final_vac_soc if final_vac_soc > 0 else 0

			penalty_for_negative_soc = - final_vac_soc/100 * unitDropPenalty * VAC_Capacity if final_vac_soc < 0 else 0
			# Value of having fin_ess_soc,fin_ev_soc and home position in next time interval
			future_value_of_p_cars_at_Park = Value[ts+1, essSoC, fin_vac_soc] + penalty_for_negative_soc
			probability_of_p_cars_at_Park = behaviorModel[ts, p]  # Probablity of p cars at home==Probability of d cars driving

			expected_future_cost += probability_of_p_cars_at_Park * future_value_of_p_cars_at_Park

		return expected_future_cost

	model = AbstractModel()

	##################################################################################################################
	##########################          Inputs setting matrices                          #############################
	##################################################################################################################

	model.T = Set()  # Index Set for time steps of optimization horizon
	model.T_SoC = Set()  # SoC of the ESSs at the end of optimization horizon are also taken into account

	model.StateRange_ESS = Set()
	model.DomainRange_ESS = Set()
	model.StateRange_EV = Set()
	model.DomainRange_EV = Set()
	model.Behavior_Model = Set(dimen=2)
	model.Value = Set()

	##################################################################################################################
	##########################          Inputs                                           #############################
	##################################################################################################################

	#####################################       Inputs: Constants      #####################################################

	model.dT = Param(within=PositiveReals)
	model.timestep = Param(within=PositiveReals)

	# Electric Vehicle
	#model.Carpark = Param(model.Number_Cars, within=Integers)     #####
	#model.Behavior_Model = Param(model.Behavior_Model_Range,model.Behavior_Model_Range, within = )  ######
	model.Number_Cars = Param(within=Integers)

	model.Unit_Consumption_Assumption = Param(within=PositiveReals)
	model.Unit_Drop_Penalty = Param(within=PositiveReals, bounds=(0, 1))
	model.vac_decision_domain = Param(model.DomainRange_EV, within=Reals)
	model.vac_soc_states = Param(model.StateRange_EV, within=PositiveReals)
	model.VAC_Capacity = Param(within=PositiveReals)

	# Photovoltaics
	model.PV_Inv_Max_Power = Param(within=PositiveReals)  # PV inverter capacity

	# Energy Storage System
	model.ess_decision_domain = Param(model.DomainRange_ESS, within=Reals)
	model.ess_soc_states = Param(model.StateRange_ESS, within=PositiveReals)

	model.ESS_Max_Charge_Power = Param(within=PositiveReals)
	model.ESS_Max_Discharge_Power = Param(within=PositiveReals)
	model.ESS_Max_SoC = Param(within=PositiveReals, bounds=(0, 1))
	model.ESS_Min_SoC = Param(within=PositiveReals, bounds=(0, 1))
	model.ESS_Capacity = Param(within=PositiveReals)

	######################################     Inputs: Real time      #####################################################
	# Electric Vehicle
	model.VAC_SoC_Value = Param(within=PositiveReals)

	# Energy Storage System
	model.SoC_Value = Param(within=PositiveReals)

	# Load
	model.P_Load = Param(model.T, within=NonNegativeReals)  # Active power demand forecast

	# Photovoltaics
	model.P_PV = Param(model.T, within=NonNegativeReals)  # PV PMPP forecast

	#######################################      Outputs       #######################################################

	# Combined decision
    model.Decision=Var(model.ess_decision_domain,model.vac_decision_domain,within=Binary)

	model.P_PV_Output=Var(within=Reals, bounds=(0,self.P_PV[model.timestep]))    ###poner restriccion de PV max 
	model.P_ESS_Output=Var(within=Reals, bounds=(-model.ESS_Max_Charge_Power,model.ESS_Max_Discharge_Power))
	model.P_GRID_Output=Var(within=Reals) #, bounds=(-self.P_Grid_Max_Export_Power,10000))
	model.P_VAC_Output=Var(within=NonNegativeReals)
	
	
	
	##################################################################################################################
	###################                      Constraints                                    ##########################
	##################################################################################################################
                         
				
	def combinatorics(model):
		# only one of the feasible decisions can be taken
		return 1==sum(model.Decision[pESS,pVAC] for pESS,pVAC in product(model.decision_ess,model.decision_vac))
	model.const_integer=Constraint(rule=combinatorics)
	
	def ess_chargepower(model):
		return model.P_ESS_Output==sum(model.Decision[pESS,pVAC]*pESS for pESS,pVAC in product(model.decision_ess,model.decision_vac))/100*model.ESS_Capacity/self.dT
	model.const_esschargepw=Constraint(rule=ess_chargepower)            
	
	def vac_chargepower(model):
		return model.P_VAC_Output == sum(model.Decision[pESS,pVAC]*pVAC for pESS,pVAC in product(model.decision_ess,model.decision_vac))/100*self.VAC_Capacity/self.dT
	model.const_evchargepw=Constraint(rule=vac_chargepower)
	
	def home_demandmeeting(model):
		# Power demand must be met anyway
		return model.P_VAC_Output + model.P_ESS_Output==model.P_PV_Output + model.P_GRID_Output
	model.const_demand=Constraint(rule=home_demandmeeting)

	def objrule1(model):
		future_cost=0

		for p_ess,p_vac in product(model.decision_ess,model.decision_vac):   #If vac is charged with one of the feasible decision 'p_ev'
							 
			fin_ess_soc = p_ess + model.SoC_Value   #Transition between ESS SOC states are always deterministic
			fin_vac_soc = p_vac + model.VAC_SoC_Value  #Transition between VAC SOC states are stochastic
			
			expected_future_cost_of_this_decision=self.calculate_expectation(model.timestep,fin_ess_soc,fin_vac_soc,model.Number_Cars,model.Unit_Consumption_Assumption, model.Unit_Drop_Penalty,model.VAC_Capacity,model.Value,model.Behavior_Model)    #Value of having fin_ess_soc and fin_vac_soc in next time interval    

			future_cost += model.Decision[p_ess,p_vac]*expected_future_cost_of_this_decision    #Adding the expected_future cost of taking 'p_ess and p_vac' decision when initial condition is combination of 'ini_ess_soc' and 'ini_vac_soc'                                     
	
		return self.P_PV[model.timestep]-model.P_PV_Output + future_cost

	model.obj=Objective(rule=objrule1,sense=minimize)
	return model
	
