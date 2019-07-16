# -*- coding: utf-8 -*-
"""
Created on Fri Aug 17 19:08:01 2018

@author: guemruekcue
"""

from itertools import product
import time
import numpy as np
import os
import pandas as pd
from itertools import chain
from functions import import_statistics
from pyomo.environ import SolverFactory
from pyomo.core import *
from carpark import CarPark,Charger,Car
import numpy as np

import ptvsd

class MaximizePV():
    
    def __init__(self,timeresolution,horizon,solver,
                 pv_max_generation,
                 ess_capacity,ess_minSoC,ess_maxSoC,
                 ess_max_charge,ess_max_discharge,
                 ess_soc_domain,ess_decision_domain,
                 vac_soc_domain,vac_decision_domain,
                 unitConsumptionAssumption,dropPenalty,
                 forecast_pv,forecast_price,
                 carPark,behaviorModel):
        """
        param timeresolution: integer
            Number of seconds in one time step
        param horizon: integer 
            Total number of time steps= Optimization horizon
        param solver: SolverFactory
            Optimization solver Glpk or Bonmin
        param pv_max_generation: float 
            PV inverter capacity: kW
        param ess_capacity: kWh
            ESS energy capacity
        param ess_minSoC: float
            Minimum allowed SoC for ESS 
        param ess_maxSoC: float
            Maximum allowed SoC for ESS               
        param ess_max_charge:    float
            ESS maximum charge power: kW
        param ess_max_discharge: float
            ESS maximum discharge power: kW 
        param ess_soc_domain : range
            For resolution of states, defines the possible SoC levels for ESS : %
        param ess_decision_domain : range
            Defines the possible decisions for ESS : % change in SoC level of ESS
        param vac_soc_domain : range
            For resolution of states, defines the possible SoC levels for VAC : % 
        param vac_decision_domain : range
            Defines the possible decisions for VAC : % change in SoC level of VAC                          
        param unitConsumptionAssumption: Integer
            Assumption on how much capacity of VAC will be spent if one car drives during one time step: %
        param dropPenalty: float
            Penalty rate for dropping below allowed 0% VAC SoC: 1/kWh
        param forecast_pv: dict
            Maximum power generation acc. weather prediction for upcoming prediction horizon (entries:kW)
        param forecast_price: dict
            Price forecast for upcoming prediction horizon (entries:EUR/MWh)
        param carPark: CarPark
            CarPark object with chargers and served fleet information
        param behaviorModel: pmfs
            Probablity mass function i.e. values are possible number of plugged cars
        """
        
        self.dT=timeresolution  #in seconds
        self.T=horizon
        self.solver=solver
        self.park=carPark     
        self.behaviorModel=behaviorModel
        self.unitConsumptionAssumption=unitConsumptionAssumption
        self.unitDropPenalty=dropPenalty
        
        self.Max_Export=0
        self.Max_PVGen=pv_max_generation

        self.ESS_Capacity=ess_capacity*3600     #ESS capacity in kWs
        self.ESS_Min_SoC=ess_minSoC
        self.ESS_Max_SoC=ess_maxSoC        
        self.ESS_Max_Charge=ess_max_charge
        self.ESS_Max_Discharge=ess_max_discharge
        
        self.VAC_Capacity=self.park.vac_capacity

        self.P_PV_Forecast=forecast_pv
        self.Price_Forecast=forecast_price

        #Decision domain for VAC and ESS charging
        self.ess_decision_domain=ess_decision_domain
        self.vac_decision_domain=vac_decision_domain

        #States
        self.ess_soc_states=ess_soc_domain
        self.vac_soc_states=vac_soc_domain                 
                
        #Initialize empty lookup tables
        keylistforValue    =[(t,s_ess,s_vac) for t,s_ess,s_vac in product(list(range(0,self.T+1)),self.ess_soc_states,self.vac_soc_states)]
        keylistforDecisions=[(t,s_ess,s_vac) for t,s_ess,s_vac in product(list(range(0,self.T)),self.ess_soc_states,self.vac_soc_states)]
        
        self.Value   =dict.fromkeys(keylistforValue)
        self.Decision=dict.fromkeys(keylistforDecisions)
    
        for t,s_ess,s_vac in product(range(0,self.T),self.ess_soc_states,self.vac_soc_states):
            self.Decision[t,s_ess,s_vac]={'PV':None,'Grid':None,'ESS':None,'VAC':None}
            self.Value[t,s_ess,s_vac]=None

        for s_ess,s_vac in product(self.ess_soc_states,self.vac_soc_states):
            self.Value[self.T,s_ess,s_vac]=1.0


    def calculate_expectation(self,ts,essSoC,vacSoC):
        """
        Calculates expected_future_cost of the decision that charges vac to vacSoC
        """
        
        expected_future_cost=0
        
        for p in range(self.park.carNb+1):
            #p: number of cars at park
            #d: number of cars driving
            d=self.park.carNb-p
            
            final_vac_soc=vacSoC-d*self.unitConsumptionAssumption
            fin_vac_soc=final_vac_soc if final_vac_soc>0 else 0
           
            penalty_for_negative_soc=-final_vac_soc/100*self.unitDropPenalty*self.VAC_Capacity if final_vac_soc<0 else 0            
            future_value_of_p_cars_at_Park=self.Value[ts+1,essSoC,fin_vac_soc]+penalty_for_negative_soc    #Value of having fin_ess_soc,fin_ev_soc and home position in next time interval                
            probability_of_p_cars_at_Park=self.behaviorModel[ts,p]  #Probablity of p cars at home==Probability of d cars driving
            
            expected_future_cost+=probability_of_p_cars_at_Park*future_value_of_p_cars_at_Park
                      
        return expected_future_cost  
        
    def optimaldecisioncalculator(self,timestep,ini_ess_soc,ini_vac_soc):
        """
        Solves the optimization problem for a particular initial state (ess_soc, vac_soc) at the time step
        """
      
        model = ConcreteModel()
                   
        feasible_Pess=[]            #Feasible charge powers to ESS under the given conditions
        for p_ESS in self.ess_decision_domain:  #When decided charging with p_ESS
            if min(self.ess_soc_states)<=p_ESS+ini_ess_soc<=max(self.ess_soc_states): #if the final ess_SoC is within the specified domain 
                feasible_Pess.append(p_ESS)                                     #then append P_ESS as one of the feasible ess decisions
        model.decision_ess=Set(initialize=feasible_Pess)
        
        feasible_Pvac=[]            #Feasible charge powers to VAC under the given conditions
        for p_VAC in self.vac_decision_domain:         #When decided charging with p_VAC   
            if p_VAC+ini_vac_soc<=max(self.vac_soc_states): #if the final vac_SoC is within the specified domain
                feasible_Pvac.append(p_VAC)                  #then append p_VAC as one of the feasible vac decisions
        model.decision_vac=Set(initialize=feasible_Pvac) 
        
        #Combined decision                   
        model.Decision=Var(model.decision_ess,model.decision_vac,within=Binary)
        
        model.P_ESS=Var(within=Reals)
        model.P_VAC=Var(within=NonNegativeReals)
        model.P_PV=Var(bounds=(0,self.P_PV_Forecast[timestep]))
        model.P_GRID=Var(within=Reals)            
                    
        def combinatorics(model):
            #only one of the feasible decisions can be taken
            return 1==sum(model.Decision[pESS,pVAC] for pESS,pVAC in product(model.decision_ess,model.decision_vac))
        model.const_integer=Constraint(rule=combinatorics)
        
        def ess_chargepower(model):
            return model.P_ESS==sum(model.Decision[pESS,pVAC]*pESS for pESS,pVAC in product(model.decision_ess,model.decision_vac))/100*self.ESS_Capacity/self.dT
        model.const_esschargepw=Constraint(rule=ess_chargepower)            
        
        def vac_chargepower(model):
            return model.P_VAC==sum(model.Decision[pESS,pVAC]*pVAC for pESS,pVAC in product(model.decision_ess,model.decision_vac))/100*self.VAC_Capacity/self.dT
        model.const_evchargepw=Constraint(rule=vac_chargepower)
        
        def home_demandmeeting(model):
            #Power demand must be met anyway
            return model.P_VAC+model.P_ESS==model.P_PV+model.P_GRID
        model.const_demand=Constraint(rule=home_demandmeeting)
    
        def objrule1(model):
            future_cost=0

            for p_ess,p_vac in product(model.decision_ess,model.decision_vac):   #If vac is charged with one of the feasible decision 'p_ev'
                                 
                fin_ess_soc=p_ess+ini_ess_soc   #Transition between ESS SOC states are always deterministic
                fin_vac_soc=p_vac+ini_vac_soc   #Transition between VAC SOC states are stochastic
                
                expected_future_cost_of_this_decision=self.calculate_expectation(timestep,fin_ess_soc,fin_vac_soc)    #Value of having fin_ess_soc and fin_vac_soc in next time interval    

                future_cost+=model.Decision[p_ess,p_vac]*expected_future_cost_of_this_decision    #Adding the expected_future cost of taking 'p_ess and p_vac' decision when initial condition is combination of 'ini_ess_soc' and 'ini_vac_soc'                                     
        
            return self.P_PV_Forecast[timestep]-model.P_PV+ future_cost

        model.obj=Objective(rule=objrule1)
        self.solver.solve(model)       
        P_VAC=model.P_VAC()
        P_ESS=model.P_ESS()
        P_GRID=model.P_GRID()
        P_PV=model.P_PV()
        V=model.obj()
                            
              
        return P_GRID,P_PV,P_ESS,P_VAC,V     
    
    def solve_dynamicprogram(self):  #Whole map calculation for dynamic programming
        """
        Calculates the optimal values of whole map
        """
        start=time.time()
        for timestep in reversed(range(0,self.T)):
            print("Timestep",timestep)
            #Solves the optimizaton problem for every initial states at the time step
            for ini_ess_soc,ini_vac_soc in product(self.ess_soc_states,self.vac_soc_states):
                results=self.optimaldecisioncalculator(timestep,ini_ess_soc,ini_vac_soc)

                self.Decision[timestep,ini_ess_soc,ini_vac_soc]['Grid']=results[0]
                self.Decision[timestep,ini_ess_soc,ini_vac_soc]['PV']=results[1]
                self.Decision[timestep,ini_ess_soc,ini_vac_soc]['ESS']=-results[2]
                self.Decision[timestep,ini_ess_soc,ini_vac_soc]['VAC']=-results[3]
                self.Value[timestep,ini_ess_soc,ini_vac_soc]=results[1]
        end=time.time()
        print("Dynamic programming execution:",end-start)
        
    def control_action(self,initial_ess_soc_value,initial_vac_soc_value):
        
        
        #self.solve_dynamicprogram()
        
        p_pv=self.Decision[0,initial_ess_soc_value,initial_vac_soc_value]['PV']
        p_grid=self.Decision[0,initial_ess_soc_value,initial_vac_soc_value]['Grid']
        p_ess=self.Decision[0,initial_ess_soc_value,initial_vac_soc_value]['ESS']
        p_vac=-self.Decision[0,initial_ess_soc_value,initial_vac_soc_value]['VAC']
        p_ev={}
        
        print("Dynamic programming calculations")
        print("PV generation:",p_pv)
        print("Import:",p_grid)
        print("ESS discharge:",p_ess)
        print("VAC charging",p_vac)
        
        
        #############################################################################
        #This section distributes virtual capacity charging power into the cars plugged chargers in the station
        
        #detect which cars are connected to the chargers in the commercial charging station
        #calculate the maximum feasible charging power input under given SoC
        connections=self.park.maxChargePowerCalculator(self.dT)  
        
        #Calculation of the feasible charging power at the commercial station
        feasible_ev_charging_power=min(sum(connections.values()),p_vac)
        
        for charger,maxChargePower in connections.items():    
            power_output_of_charger=maxChargePower/feasible_ev_charging_power
            p_ev[charger]=power_output_of_charger
        #############################################################################
        
        #############################################################################
        #This section decides what to do with the non utilized virtual capacity charging power
        
        #Power leftover: Non implemented part of virtual capacity charging power
        leftover_vac_charging_power=p_vac-feasible_ev_charging_power
        
        #Leftover is attempted to be removed with less import
        less_import=min(p_grid,leftover_vac_charging_power)
        p_grid=p_grid-less_import
       
        #Some part could be still left
        still_leftover=leftover_vac_charging_power-less_import
             
        #Still leftover is attempted to be charged to the ESS
        ess_charger_limit=self.ESS_Max_Charge
        ess_capacity_limit=(100-initial_ess_soc_value)/100*self.ESS_Capacity/self.dT
        max_ess_charging_power=min(ess_charger_limit,ess_capacity_limit,still_leftover)               
        p_ess=p_ess-max_ess_charging_power
        
        #Final leftover: if the ESS does not allow charging all leftover, final leftover will be compensated by PV curtailment
        final_leftover=still_leftover-max_ess_charging_power
        p_pv=p_pv-final_leftover
        
        print("Implemented actions")
        print("PV generation:",p_pv)
        print("Import:",p_grid)
        print("ESS discharge:",p_ess)
        print("Real EV charging",feasible_ev_charging_power)
        
        return p_pv,p_grid,p_ess,p_ev
         

if __name__ == "__main__":

    charger1=Charger(7)
    charger2=Charger(7)
    charger3=Charger(7)
    charger4=Charger(22)
    charger5=Charger(22)
    #charger6=Charger(6)
    #charger7=Charger(6)
    chargers=[charger1,charger2,charger3,charger4,charger5]#,charger6,charger7]
    car1=Car(18.7)
    car2=Car(18.7)
    car3=Car(18.7)
    car4=Car(18.7)
    car5=Car(18.7)
    #car6=Car(30)
    #car7=Car(30)
    car1.setSoC(0.2)
    car2.setSoC(0.2)
    car3.setSoC(0.2)
    car4.setSoC(0.2)
    car5.setSoC(0.2)
    #car6.setSoC(0.5)
    #car7.setSoC(0.5)
    charger1.plug(car1)
    charger2.plug(car2)
    charger3.plug(car3)
    charger4.plug(car4)
    charger5.plug(car5)
    cars=[car1,car2,car3,car4,car5]#,car6,car7]
    mycarpark=CarPark(chargers,cars)


    timeresolution=3600
    horizon=24
    theSolver=SolverFactory("cbc")




    Forecast_inp='/usr/src/app/stochastic_optimizer/Forecasts_60M.xlsx'
    Behavior_inp='/usr/src/app/stochastic_optimizer/PMFs_60M.csv'
    xl= pd.ExcelFile(Forecast_inp)
    forecasts  = xl.parse("0")
    behavMod=import_statistics(Behavior_inp,"00:00",7)

    forecast_pv=dict(enumerate(forecasts['PV'].values.tolist()))
    forecast_price=dict(enumerate(forecasts['Price'].values.tolist()))
    ess_max_charge=33#0.62
    ess_max_discharge=33#0.62
    grid_max_export=1000#10
    pv_max_generation=50#1.5
    ess_capacity=70#0.675
    ess_minSoC=0.2
    ess_maxSoC=1.0
    ess_soc_domain=range(0,110,10)
    ess_decision_domain=range(-40,50,10)#(-40,20,10)
    vac_soc_domain=[x * 0.1 for x in range(0, 1025,25)] #np.linspace(0,100.0,2.5,endpoint=True)
    vac_decision_domain=[x * 0.1 for x in range(0, 225,25)] #np.linspace(0.0,20.0,2.5,endpoint=True)

    unitConsumptionAssumption=2.5
    dropPenalty=1


    optimizer=MaximizePV(timeresolution,horizon,theSolver,pv_max_generation,
                    ess_capacity,ess_minSoC,ess_maxSoC,
                    ess_max_charge,ess_max_discharge,
                    ess_soc_domain,ess_decision_domain,
                    vac_soc_domain,vac_decision_domain,
                    unitConsumptionAssumption,dropPenalty,
                    forecast_pv,forecast_price,
                    mycarpark,behavMod)


    optimizer.solve_dynamicprogram()


    optimizer.control_action(40,20)
