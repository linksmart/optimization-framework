# -*- coding: utf-8 -*-
"""
Created on Wed Apr 25 17:17:12 2018

@author: guemruekcue
"""

from pyomo.environ import SolverFactory
from pyomo.core import *
from itertools import product

class StochasticDynamicProgram():
    
    def __init__(self,scenarioParameters,ess_soc_domain,ev_soc_domain,solver,objective,probability_plug,probability_end_soc):
        """
        ess_soc_domain:  Defines the domain for ESS_SoC values e.g. [30,40,50,60,70]
        ev_soc_domain:   Defines the domain for EV_SoC values  e.g. [30,40,50,60,70]
        """
        self.solver=solver
        self.objective=objective
        
        # Time parameters
        self.T=scenarioParameters.T  #Total number of time steps: Optimization horizon
        self.dT=24*60*60/self.T      #Size of one time step: in seconds
        
        #Time invariant parameters
        self.PV_Inv_Max_Power       =scenarioParameters.PV_Inv_Max_Power
        self.P_Grid_Max_Export_Power=scenarioParameters.P_Grid_Max_Export_Power
        self.ESS_Min_SoC            =scenarioParameters.ESS_Min_SoC
        self.ESS_Max_SoC            =scenarioParameters.ESS_Max_SoC
        self.ESS_Capacity           =scenarioParameters.ESS_Capacity
        self.ESS_Max_Charge_Power   =scenarioParameters.ESS_Max_Charge_Power
        self.ESS_Max_Discharge_Power=scenarioParameters.ESS_Max_Discharge_Power     
        
        self.EV_Min_SoC=scenarioParameters.EV_Min_SoC
        self.EV_Max_SoC=scenarioParameters.EV_Max_SoC
        self.EV_Capacity = scenarioParameters.EV_Capacity
        self.EV_Max_Charge_Power= scenarioParameters.EV_Max_Charge_Power
        self.EV_Max_Drive_Power= scenarioParameters.EV_Max_Drive_Power
              
        #Forecasts
        self.P_Load_Forecast =scenarioParameters.P_Load_Forecast
        self.P_PV_Forecast   =scenarioParameters.P_PV_Forecast
            
        #Real-time data
        #self.ESS_SoC_Value =scenarioParameters.ESS_SoC_Value
        
        #Deficit SoC penalty
        self.unitpenalty=0.5
        
        #Indices
        self.timeIndexSet =list(range(0,self.T))      #Will be represented as t
        self.valueIndexSet=list(range(0,self.T+1))     #Will be represented as t  
        self.stateIndexSet_ess_soc=ess_soc_domain
        self.stateIndexSet_ev_soc =ev_soc_domain
        self.stateIndexSet_ev_plug=[0,1]
        
        #Initialize empty lookup tables
        keylistforValue    =[(t,s1,s2,s3) for t,s1,s2,s3 in product(self.timeIndexSet ,self.stateIndexSet_ess_soc,self.stateIndexSet_ev_soc,self.stateIndexSet_ev_plug)]
        keylistforDecisions=[(t,s1,s2,s3) for t,s1,s2,s3 in product(self.timeIndexSet ,self.stateIndexSet_ess_soc,self.stateIndexSet_ev_soc,self.stateIndexSet_ev_plug)]
        
        self.Value   =dict.fromkeys(keylistforValue)
        self.Decision=dict.fromkeys(keylistforDecisions)
    
        for t,s1,s2,s3 in product(self.timeIndexSet ,self.stateIndexSet_ess_soc,self.stateIndexSet_ev_soc,self.stateIndexSet_ev_plug):
            self.Decision[t,s1,s2,s3]={'PV':None,'Grid':None,'ESS':None,'EV':None,'EV_FinalSoC':None,'ESS_FinalSoC':None}
        
        for s1,s2,s3 in product(self.stateIndexSet_ess_soc,self.stateIndexSet_ev_soc,self.stateIndexSet_ev_plug):
            
            if s2>self.EV_Min_SoC:
                #No inherent value of end state cases if EV_SoC>self.EV_Min_SoC
                self.Value[self.T,s1,s2,s3]=0
            else:
                self.Value[self.T,s1,s2,s3]=(s2-self.EV_Min_SoC)/100*self.EV_Capacity*self.unitpenalty
            
        
        #Narrowing down the solution space by removing the infeasible range of final states: ESS_SoC
        self.feasibleSoCRange_ess=dict.fromkeys(self.stateIndexSet_ess_soc)        
        for iniSoC in self.feasibleSoCRange_ess.keys():
            
            max_Final_SoC=iniSoC+self.ESS_Max_Charge_Power/self.ESS_Capacity*100 
            min_Final_SoC=iniSoC-self.ESS_Max_Discharge_Power/self.ESS_Capacity*100
        
            feasibleRange=list(filter(lambda x: max_Final_SoC>=x >=min_Final_SoC, self.stateIndexSet_ess_soc))
            self.feasibleSoCRange_ess[iniSoC]=feasibleRange
                      
        self.probability_plug=probability_plug
        self.probability_end_soc=probability_end_soc
        
    def optimaldecisioncalculator(self,timestep,ess_initialSoC,ev_initialSoC,ev_ini_plug):
        """
        Solves the optimization problem for a particular initial state at the time step
        """
        
        
        model = ConcreteModel()
        model.states_ess_soc=Set(initialize=self.feasibleSoCRange_ess[ess_initialSoC])
        model.states_ev_soc =Set(initialize=self.stateIndexSet_ev_soc)
        model.states_ess_plug=Set(initialize=[0,1])

        finalsocdict={}
        for state in model.states_ess_soc:
            finalsocdict[state]=state
            
        #model.probabilities=Param(model.time,model.states,initialize=self.probabilities)
        model.P_EV=Var(bounds=(0,ev_ini_plug*self.EV_Max_Charge_Power))     
    
        model.P_PV=Var(bounds=(0,self.P_PV_Forecast[timestep]))
        model.P_ESS=Var(bounds=(-self.ESS_Max_Charge_Power,self.ESS_Max_Discharge_Power))
        model.P_GRID=Var(bounds=(-self.P_Grid_Max_Export_Power,10000))
        
        model.P_EV_deficit=Var(within=NonNegativeReals)
        
        
        lb=int(min(model.states_ess_soc)/10)
        ub=int(max(model.states_ess_soc)/10)
        model.ESS_SoC=Var(within=Integers,bounds=(lb,ub))
                   
        def demandmeeting(model):
            return self.P_Load_Forecast[timestep]+model.P_EV==model.P_PV+model.P_ESS+model.P_GRID
        model.const_demand=Constraint(rule=demandmeeting)
        
        def final_ess_soc(model):
            return self.ESS_Min_SoC<=model.ESS_SoC*10<=self.ESS_Max_SoC
            #return self.ESS_Min_SoC<=ess_initialSoC-model.P_ESS/self.ESS_Capacity*100<=self.ESS_Max_SoC
        model.const_ess_soc=Constraint(rule=final_ess_soc)
        
        def delta_ess_soc(model):
            return model.ESS_SoC*10==ess_initialSoC-model.P_ESS/self.ESS_Capacity*100
        model.const_ess_soc2=Constraint(rule=delta_ess_soc)
        
        def delta_ev_soc(model):
            #return self.EV_Min_SoC<=ev_initialSoC+model.P_EV+model.P_EV_deficit/self.EV_Capacity*100<=self.EV_Max_SoC
            return ev_initialSoC+model.P_EV/self.EV_Capacity*100<=self.EV_Max_SoC
        model.const_ev_soc=Constraint(rule=delta_ev_soc)

        def ev_energy_deficit(model):
            return model.P_EV_deficit==self.EV_Capacity/100*(self.EV_Max_SoC-ev_initialSoC)-model.P_EV
        model.const_ev_deficit_soc=Constraint(rule=ev_energy_deficit)
        
        prob={}
        for fin_ess_soc in self.feasibleSoCRange_ess[ess_initialSoC]:
            #Probability of ending up with 'fin_ess_soc'
            prob_ess_final=1/len(self.feasibleSoCRange_ess[ess_initialSoC]) #uniformal
            for ev_fin_plug in [0,1]:
                #Probability of switching grom 'ev_ini_plug' to 'ev_fin_plug': From markov chain transition matrix  
                prob_plug=self.probability_plug[timestep,ev_ini_plug,ev_fin_plug]              
                                
                #If ev is not plugged-in at the next step
                if ev_fin_plug==0:
                    #Probability of ending up with 'ev_fin_plug'
                    prob_ev_final=dict.fromkeys(self.stateIndexSet_ev_soc,1/len(self.stateIndexSet_ev_soc))
                
                #If ev is plugged-in now and at the next step
                elif ev_ini_plug==1:
                    #Probability of ending up with 'ev_fin_plug'
                    prob_ev_final=dict.fromkeys(self.stateIndexSet_ev_soc,1/len(self.stateIndexSet_ev_soc))
                    
                #If ev is not plugged-in now and but plugged-in at the next step
                elif ev_ini_plug==0:
                    #Probability of ending up with 'ev_fin_plug'
                    prob_ev_final={}
                    for soc in self.stateIndexSet_ev_soc:
                        prob_ev_final[soc]=self.probability_end_soc[soc]
                    
                for fin_ev_soc in self.stateIndexSet_ev_soc:
                    prob[fin_ess_soc,fin_ev_soc,ev_fin_plug]=prob_ess_final*prob_plug*prob_ev_final[fin_ev_soc]
                    
          
        def objrule0(model):
            return model.P_GRID*model.P_GRID+self.unitpenalty*self.unitpenalty*model.P_EV_deficit*model.P_EV_deficit+sum(prob[s1,s2,s3]*self.Value[timestep+1,s1,s2,s3] for s1,s2,s3 in product(model.states_ess_soc,self.stateIndexSet_ev_soc,self.stateIndexSet_ev_plug))        
        def objrule1(model):
            return (self.P_PV_Forecast[timestep]-model.P_PV)+self.unitpenalty*model.P_EV_deficit+sum(prob[s1,s2,s3]*self.Value[timestep+1,s1,s2,s3] for s1,s2,s3 in product(model.states_ess_soc,self.stateIndexSet_ev_soc,self.stateIndexSet_ev_plug))
             
        if self.objective==0:
            model.obj=Objective(rule=objrule0,sense=minimize)
        elif self.objective==1:
            model.obj=Objective(rule=objrule1,sense=minimize)        
        
        result=self.solver.solve(model)
        
        
        P_PV=model.P_PV()
        P_ESS=model.P_ESS()
        P_GRID=model.P_GRID()
        P_EV=model.P_EV()
        
        ess_finalsoc=int(ess_initialSoC-model.P_ESS()/self.ESS_Capacity*100)
        ev_finalsoc=int(ev_initialSoC+model.P_EV()/self.EV_Capacity*100)
        V=model.obj()
        
        #if (timestep,ess_initialSoC,ev_initialSoC,ev_ini_plug)==(3,30,30,1):
        #    print("Optimal decision at",timestep,ess_initialSoC,ev_initialSoC,ev_ini_plug)
        #    print(P_PV,P_ESS,P_GRID,P_EV,model.P_EV_deficit(),ess_finalsoc,ev_finalsoc,V)
        #print(result.solver.time)
        
                   
        return P_PV,P_ESS,P_GRID,P_EV,ess_finalsoc,ev_finalsoc,V       
    
    def findstateoptimals(self,timestep):
        """
        Solves the optimizaton problem for every initial states at the time step
        """
        print("Time step",timestep)
        for s1,s2,s3 in product(self.stateIndexSet_ess_soc,self.stateIndexSet_ev_soc,self.stateIndexSet_ev_plug):
            results=self.optimaldecisioncalculator(timestep,s1,s2,s3)
            
            self.Decision[timestep,s1,s2,s3]['PV']  =results[0]
            self.Decision[timestep,s1,s2,s3]['ESS'] =results[1]
            self.Decision[timestep,s1,s2,s3]['Grid']=results[2]
            self.Decision[timestep,s1,s2,s3]['EV']=results[3]
            self.Decision[timestep,s1,s2,s3]['ESS_FinalSoC']=results[4]
            self.Decision[timestep,s1,s2,s3]['EV_FinalSoC']=results[5]
            self.Value[timestep,s1,s2,s3]=results[6]
            
    def wholeMapCalculation(self):
        """
        Calculates the optimal values of whole map
        """
        for timestep in reversed(self.timeIndexSet):
            self.findstateoptimals(timestep)
            
    def findoptimalValues(self,t,ESS_SoC_Value,EV_SoC_Value,ifPlugged):
        """
        Solves the dynamic program to calculate the optimal actions
        """
        P_PV=self.Decision[t,ESS_SoC_Value,EV_SoC_Value,ifPlugged]['PV']
        P_ESS=self.Decision[t,ESS_SoC_Value,EV_SoC_Value,ifPlugged]['ESS']
        P_Grid=self.Decision[t,ESS_SoC_Value,EV_SoC_Value,ifPlugged]['Grid']
        P_EV=self.Decision[t,ESS_SoC_Value,EV_SoC_Value,ifPlugged]['EV']
        ESS_SoC=self.Decision[t,ESS_SoC_Value,EV_SoC_Value,ifPlugged]['ESS_FinalSoC']
        EV_SoC=self.Decision[t,ESS_SoC_Value,EV_SoC_Value,ifPlugged]['EV_FinalSoC']
        #print(t,ESS_SoC_Value,EV_SoC_Value,ifPlugged,P_EV)
        return P_PV,P_ESS,P_Grid,P_EV,ESS_SoC,EV_SoC
     
