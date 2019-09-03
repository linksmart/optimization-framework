# -*- coding: utf-8 -*-
"""
Created on Tue Aug 14 17:14:02 2018

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


class MinimizeGrid():
    
    def __init__(self,timeresolution,horizon,solver,
                 ev_capacity,ev_soc_domain,ev_decision_domain,unitconsumption,
                 ess_capacity,ess_soc_domain,ess_decision_domain,
                 markovModel,ev_minSoC,dropPenalty,
                 forecast_load,forecast_pv,forecast_price,
                 ess_max_charge,ess_max_discharge,grid_max_export,pv_max_generation,
                 ess_minSoC,ess_maxSoC,
                 ess_iniSoC,ev_iniSoC,ev_iniPos):
        """
        param timeresolution: integer
            Number of seconds in one time step
        param horizon: integer 
            Total number of time steps= Optimization horizon
        param solver: SolverFactory
            Optimization solver: Bonmin            
        param ev_capacity   : float 
            Capacity of EV Battery Capacity: kWh        
        param unitconsumption: Integer
            Assumption on how much capacity of EV battery will be spent if one car drives during one hour: %
        param markovModel: Dictionary
            Markov transition matrices
        param ev_decision_domain : range
            Defines the possible decisions for EV charging : % change in SoC level of EV
        >>>Example
            ev_decision_domain=[0,5,10]
            >>> Charger can charge 5% or 10% of EV during time step
        param ev_soc_domain : range
            For resolution of states, defines the possible SoC levels for EV : %            
        >>>Example
            ev_soc_domain=[0,5,15,....,100]
            >>> DP states are combination of position and ev_soc 
            >>> i.e. at ts=12 having away state and ev_soc=40%
        param ess_capacity:
            Capacity of EV Battery Capacity: kWh
        param ess_soc_domain: range
            For resolution of states, defines the possible SoC levels for ESS : %    
        param ess_decision_domain: range
            Defines the possible decisions for ESS charging : % change in SoC level of ESS        
        param markovModel: dictionary
            Inhomogenous markov model for state transitions between home-away states
        param ev_minSoC: float
            Allowed minimum SoC of EV battery
        param dropPenalty: float
            Penalty rate for dropping below allowed min EV SoC: 1/kWh
        param forecast_load: dict 
            Active power forecast for upcoming prediction horizon (entries:kW)
        param forecast_pv: dict
            Maximum power generation acc. weather prediction for upcoming prediction horizon (entries:kW)
        param forecast_price: dict
            Price forecast for upcoming prediction horizon (entries:EUR/MWh)
        param ess_max_charge:    float
            ESS maximum charge power: kW
        param ess_max_discharge: float
            ESS maximum discharge power: kW
        param grid_max_export:   float
            Maximum export(feed-in) to grid :kW
        param pv_max_generation: float 
            PV inverter capacity: kW
        param ess_capacity: kWh
            ESS energy capacity
        param ess_minSoC: float
            Minimum allowed SoC for ESS 
        param ess_maxSoC: float
            Maximum allowed SoC for ESS
        param ess_iniSoC: float
            Initial SoC of ESS
        param ev_iniSoC: float
            Initial SoC of EV battery
        param ev_iniPos: integer
            Initial position of EV
            1: Home
            0: Away
        """
        self.dT=timeresolution  #in seconds
        self.T=horizon
        self.solver=solver       
        
        self.ev_capacity=ev_capacity*3600                               #EV battery capacity in kW-sec
        self.consumptionAssumption=int(unitconsumption/3600*self.dT)    #How much SoC of EV battery is assumed to be consumed when one car drives for one time step length
        self.ev_minSoC=int(ev_minSoC*100)       #Allowed minimum EV battery SoC %
        self.unitDropPenalty=dropPenalty/3600   #Penalty for compensation of 1kW-sec in case dropping below allowed minimum EV SoC         
        self.max_car_atHome=1
                      
        self.markovModel=markovModel           #Inhomogenous markov model: dict        
        self.max_car_atHome=1                  #Max number of cars at home one time step
        
        #Decision domain for EV Battery and ESS charging
        self.ev_decision_domain=ev_decision_domain
        self.ess_decision_domain=ess_decision_domain
        
        #States
        self.ess_soc_states=ess_soc_domain
        self.ev_soc_states=ev_soc_domain
        self.ev_pos_states=range(2)
        
        #Initialize empty lookup tables
        keylistforValue    =[(t,s_ess,s_ev,s_pos) for t,s_ess,s_ev,s_pos in product(list(range(0,self.T+1)),self.ess_soc_states,self.ev_soc_states,self.ev_pos_states)]
        keylistforDecisions=[(t,s_ess,s_ev,s_pos) for t,s_ess,s_ev,s_pos in product(list(range(0,self.T))  ,self.ess_soc_states,self.ev_soc_states,self.ev_pos_states)]
        
        self.Value   =dict.fromkeys(keylistforValue)
        self.Decision=dict.fromkeys(keylistforDecisions)
    
        for t,s_ess,s_ev,s_pos in product(list(range(0,self.T))  ,self.ess_soc_states,self.ev_soc_states,self.ev_pos_states):
            self.Decision[t,s_ess,s_ev,s_pos]={'PV':None,'Grid':None,'ESS':None,'EV':None}
            self.Value[t,s_ess,s_ev,s_pos]=None

        for s_ess,s_ev,s_pos in product(self.ess_soc_states,self.ev_soc_states,self.ev_pos_states):
            self.Value[self.T,s_ess,s_ev,s_pos]=5.0
            
        #Parameters for ESS optimization       
        self.P_Load_Forecast=forecast_load
        self.P_PV_Forecast=forecast_pv
        self.Price_Forecast=forecast_price
        
        self.ESS_Max_Charge=ess_max_charge
        self.ESS_Max_Discharge=ess_max_discharge
        self.Max_Export=grid_max_export
        self.Max_PVGen=pv_max_generation
        
        self.ESS_Capacity=ess_capacity*3600     #ESS capacity in kWs
        self.ESS_Min_SoC=ess_minSoC
        self.ESS_Max_SoC=ess_maxSoC
        
        self.ESS_Ini_SoC=ess_iniSoC
        self.EV_Ini_SoC=ev_iniSoC
        self.EV_Ini_POS=ev_iniPos
        
    def optimaldecisioncalculator(self,timestep,ini_ess_soc,ini_ev_soc,ini_pos):
        """
        Solves the optimization problem for a particular initial state (ess_soc, ev_soc and position) at the time step
        """
        
        #Solve the optimization problem with P_EV variable
        if ini_pos==1:
       
            model = ConcreteModel()
                       
            feasible_Pess=[]            #Feasible charge powers to ESS under the given conditions
            parameters_Pess={}
            for p_ESS in self.ess_decision_domain:  #When decided charging with p_ESS
                if min(self.ess_soc_states)<=p_ESS+ini_ess_soc<=max(self.ess_soc_states): #if the final ess_SoC is within the specified domain 
                    feasible_Pess.append(p_ESS)                                     #then append P_ESS as one of the feasible ess decisions
                    parameters_Pess[p_ESS]=p_ESS    
            model.decision_ess=Set(initialize=feasible_Pess)
            
            feasible_Pev=[]            #Feasible charge powers to EV under the given conditions
            parameters_Pev={}                      
            for p_EV in self.ev_decision_domain:         #When decided charging with p_EV   
                if p_EV+ini_ev_soc<=max(self.ev_soc_states): #if the final ev_SoC is within the specified domain
                    feasible_Pev.append(p_EV)                  #then append p_EV as one of the feasible vac decisions
                    parameters_Pev[p_EV]=p_EV      
            model.decision_ev=Set(initialize=feasible_Pev) 
            
            #Combined decision                   
            model.Decision=Var(model.decision_ess,model.decision_ev,within=Binary)
            
            model.P_ESS=Var(within=Reals)
            model.P_EV=Var(within=NonNegativeReals)
            model.P_PV=Var(bounds=(0,self.P_PV_Forecast[timestep]))
            model.P_GRID=Var(within=Reals)            
                        
            def combinatorics(model):
                #only one of the feasible decisions can be taken
                return 1==sum(model.Decision[pESS,pEV] for pESS,pEV in product(model.decision_ess,model.decision_ev))
            model.const_integer=Constraint(rule=combinatorics)
            
            def ess_chargepower(model):
                return model.P_ESS==sum(model.Decision[pESS,pEV]*pESS for pESS,pEV in product(model.decision_ess,model.decision_ev))/100*self.ESS_Capacity/self.dT
            model.const_esschargepw=Constraint(rule=ess_chargepower)            
            
            def ev_chargepower(model):
                return model.P_EV==sum(model.Decision[pESS,pEV]*pEV for pESS,pEV in product(model.decision_ess,model.decision_ev))/100*self.ev_capacity/self.dT
            model.const_evchargepw=Constraint(rule=ev_chargepower)
            
            def home_demandmeeting(model):
                #Power demand must be met anyway
                return self.P_Load_Forecast[timestep]+model.P_EV+model.P_ESS==model.P_PV+model.P_GRID
            model.const_demand=Constraint(rule=home_demandmeeting)
        
            def objrule1(model):
                future_cost=0
    
                for p_ess,p_ev in product(model.decision_ess,model.decision_ev):   #If EV is charged with one of the feasible decision 'p_ev'
                                     
                    fin_ess_soc=p_ess+ini_ess_soc#Transition between ESS SOC states are always deterministic
                    fin_ev_soc=p_ev+ini_ev_soc   #Transition between EV SOC states are deterministic when the car is at home now
                    
                    valueOf_home=self.Value[timestep+1,fin_ess_soc,fin_ev_soc,1]    #Value of having fin_ess_soc,fin_ev_soc and home position in next time interval    
                    valueOf_away=self.Value[timestep+1,fin_ess_soc,fin_ev_soc,0]    #Value of having fin_ess_soc,fin_ev_soc and away position in next time interval
                    
                    #Expected future value= probability of swiching to home state*value of having home state
                    #                       +probability of swiching to away state*value of having away state
                    expected_future_cost=self.markovModel[timestep,1,1]*valueOf_home+self.markovModel[timestep,1,0]*valueOf_away
    
                    future_cost+=model.Decision[p_ess,p_ev]*expected_future_cost    #Adding the expected_future cost of taking 'p_ess and p_ev' decision when initial condition is combination of 'ini_ess_soc','ini_ev_soc' and home state                                      
            
                return model.P_GRID*model.P_GRID+ future_cost
        
            model.obj=Objective(rule=objrule1)
            self.solver.solve(model)       
            P_EV=model.P_EV()
            P_ESS=model.P_ESS()
            P_GRID=model.P_GRID()
            P_PV=model.P_PV()
            V=model.obj()
                            
        #If the car is not at home P_EV=0 is a parameter
        elif ini_pos==0:

            model = ConcreteModel()
                       
            feasible_Pess=[]            #Feasible charge powers to ESS under the given conditions
            parameters_Pess={}
            for p_ESS in self.ess_decision_domain:  #When decided charging with p_ESS
                if min(self.ess_soc_states)<=p_ESS+ini_ess_soc<=max(self.ess_soc_states): #if the final ess_SoC is within the specified domain 
                    feasible_Pess.append(p_ESS)                                     #then append P_ESS as one of the feasible ess decisions
                    parameters_Pess[p_ESS]=p_ESS    
            model.decision_ess=Set(initialize=feasible_Pess)
            
            model.Decision=Var(model.decision_ess,within=Binary)
            
            model.P_ESS=Var(within=Reals)
            model.P_EV=0
            model.P_PV=Var(bounds=(0,self.P_PV_Forecast[timestep]))
            model.P_GRID=Var(within=Reals)
            
            def combinatorics(model):
                #only one of the feasible decisions can be taken
                return 1==sum(model.Decision[pESS] for pESS in model.decision_ess)
            model.const_integer=Constraint(rule=combinatorics)
            
            def ess_chargepower(model):
                return model.P_ESS==sum(model.Decision[pESS]*pESS for pESS in model.decision_ess)/100*self.ESS_Capacity/self.dT
            model.const_esschargepw=Constraint(rule=ess_chargepower)            
                        
            def home_demandmeeting(model):
                #Power demand must be met anyway
                return self.P_Load_Forecast[timestep]+model.P_EV+model.P_ESS==model.P_PV+model.P_GRID
            model.const_demand=Constraint(rule=home_demandmeeting)
            
            def objrule0(model):
                future_cost=0             
                
                final_ev_soc=ini_ev_soc-self.max_car_atHome*self.consumptionAssumption #The car reaches to 'final_ev' by driving during one time interval
                fin_ev_soc=final_ev_soc if final_ev_soc>=self.ev_minSoC else self.ev_minSoC #The case after dropping below ev_minSoC will be considered as if they dropped to ev_minSoC%
                                                    
                for p_ess in model.decision_ess:
                                        
                    fin_ess_soc=p_ess+ini_ess_soc#Transition between ESS SOC states are always deterministic
                                      
                    #Extra penalty for dropping below predefined ev_minSoC limit
                    penalty_for_negative_soc_home=(self.ev_minSoC-final_ev_soc)/100*self.unitDropPenalty*self.ev_capacity if final_ev_soc<self.ev_minSoC else 0
                    penalty_for_negative_soc_away=(self.ev_minSoC-final_ev_soc)/100*self.unitDropPenalty*self.ev_capacity if final_ev_soc<self.ev_minSoC else 0

                    valueOf_home=self.Value[timestep+1,fin_ess_soc,fin_ev_soc,1]+penalty_for_negative_soc_home    #Value of having fin_ess_soc,fin_ev_soc and home position in next time interval    
                    valueOf_away=self.Value[timestep+1,fin_ess_soc,fin_ev_soc,0]+penalty_for_negative_soc_away    #Value of having fin_ess_soc,fin_ev_soc and away position in next time interval 
  
                    #Expected future value= probability of swiching to home state*value of having home state
                    #                       +probability of swiching to away state*value of having away state
                    expected_future_cost=self.markovModel[timestep,0,1]*valueOf_home+self.markovModel[timestep,0,0]*valueOf_away
                                        
                    future_cost+=model.Decision[p_ess]*+expected_future_cost    #Adding the expected_future cost of taking 'p_ess and p_ev' decision when initial condition is combination of 'ini_ess_soc','ini_ev_soc' and home state                                      
            
                return model.P_GRID*model.P_GRID+ future_cost

            model.obj=Objective(rule=objrule0) 
            
            self.solver.solve(model)       
            P_EV=model.P_EV
            P_ESS=model.P_ESS()
            P_GRID=model.P_GRID()
            P_PV=model.P_PV()
            V=model.obj() 
              
        return P_GRID,P_PV,P_ESS,P_EV,V                     

    def solve_dynamicprogram(self):  #Whole map calculation for dynamic programming
        """
        Calculates the optimal values of whole map
        """
        start=time.time()
        for timestep in reversed(range(0,self.T)):
            #Solves the optimizaton problem for every initial states at the time step
            for ini_ess_soc,ini_ev_soc,position in product(self.ess_soc_states,self.ev_soc_states,self.ev_pos_states):
                results=self.optimaldecisioncalculator(timestep,ini_ess_soc,ini_ev_soc,position)

                self.Decision[timestep,ini_ess_soc,ini_ev_soc,position]['Grid']=results[0]
                self.Decision[timestep,ini_ess_soc,ini_ev_soc,position]['PV']=results[1]
                self.Decision[timestep,ini_ess_soc,ini_ev_soc,position]['ESS']=-results[2]
                self.Decision[timestep,ini_ess_soc,ini_ev_soc,position]['EV']=-results[3]
                self.Value[timestep,ini_ess_soc,ini_ev_soc,position]=results[1]
        end=time.time()
        print("Dynamic programming execution:",end-start)
        

    def optimize_full_EM(self):
        
        print("Optimizer started")
        ini_EV_pos=self.EV_Ini_POS
        ini_EV_soc=min(self.ev_soc_states, key=lambda x:abs(x-self.EV_Ini_SoC*100))
        ini_ESS_soc=min(self.ess_soc_states, key=lambda x:abs(x-self.ESS_Ini_SoC*100))

        self.solve_dynamicprogram()
        optimal={}
        optimal["P_Grid"]=self.Decision[0,ini_ESS_soc,ini_EV_soc,ini_EV_pos]['Grid']
        optimal["P_PV"]  =self.Decision[0,ini_ESS_soc,ini_EV_soc,ini_EV_pos]['PV']
        optimal["P_ESS"] =self.Decision[0,ini_ESS_soc,ini_EV_soc,ini_EV_pos]['ESS']
        optimal["P_EV"]  =self.Decision[0,ini_ESS_soc,ini_EV_soc,ini_EV_pos]['EV']

        print("ESS operation optimized")         
        return optimal
           
    
                
#%%
if __name__ == "__main__":
    # EVFirst_dir=os.path.dirname(__file__)
    # AllAproaches_dir=os.path.dirname(__file__)
    Inputs_dir = os.path.join("/usr/src/app/examples", 'Inputs')
    Forecast_inp = Inputs_dir + '/Forecasts_60M.xlsx'
    Markov_inp = Inputs_dir + '/Markov_60M.csv'
    DSO_inp = Inputs_dir + '/GessCon_60M.xlsx'
    xl= pd.ExcelFile(Forecast_inp)
    xl_dso=pd.ExcelFile(DSO_inp)
    forecasts  = xl.parse("0")    
    
    #DP parameters
    timeresolution=3600
    horizon=24
    theSolver= SolverFactory("bonmin")
    #theSolver= SolverFactory("bonmin", executable="C:/cygwin/home/bonmin/Bonmin-1.8.6/build/bin/bonmin")
    ev_capacity=40
    evSoCdomain=range(0,105,5)
    evDecisionDomain=range(0,15,5)
    unitconsumption=10  #10% SoC per hour
    markovModel=import_statistics(Markov_inp,'00:00')
    ev_minSoC=0.2
    dropPenalty=1   #1/kWh
         
    forecast_load=dict(enumerate(forecasts['Load'].values.tolist()))
    forecast_pv=dict(enumerate(forecasts['PV'].values.tolist()))
    forecast_price=dict(enumerate(forecasts['Price'].values.tolist()))
    ess_max_charge=0.62
    ess_max_discharge=0.62
    grid_max_export=10
    pv_max_generation=1.5
    ess_capacity=0.675
    ess_minSoC=0.2
    ess_maxSoC=1.0
    ess_soc_domain=range(0,110,10)
    ess_decision_domain=range(-10,20,10)
    
    ess_iniSoC=0.43
    ev_iniSoC=0.2
    ev_iniPos=1
           
    EMOptimizer=MinimizeGrid(timeresolution,horizon,theSolver,
                          ev_capacity,evSoCdomain,evDecisionDomain,unitconsumption,
                          ess_capacity,ess_soc_domain,ess_decision_domain,
                          markovModel,ev_minSoC,dropPenalty,
                          forecast_load,forecast_pv,forecast_price,
                          ess_max_charge,ess_max_discharge,grid_max_export,pv_max_generation,
                          ess_minSoC,ess_maxSoC,
                          ess_iniSoC,ev_iniSoC,ev_iniPos)
    #%%
    EMOptimizer.optimaldecisioncalculator(23,50,50,1)
    optimal=EMOptimizer.optimize_full_EM()
    print(optimal)

