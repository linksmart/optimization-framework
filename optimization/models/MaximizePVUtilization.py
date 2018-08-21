# -*- coding: utf-8 -*-
"""
Created on Wed Apr 11 16:35:50 2018

@author: guemruekcue
"""


from pyomo.core import *


class Model:
    """
    Class for the abstract optimization model
    Objective: Maximization of utilized PV potential (minimization of non utilized PV potential)
    Solvers  : "bonmin","ipopt"
    """
    
    model = AbstractModel()
    
    model.N=Set()                                                   #Index Set for energy storage system devices
    model.T=Set()                                                   #Index Set for time steps of optimization horizon
    model.T_SoC=Set()                                               #SoC of the ESSs at the end of optimization horizon are also taken into account
        
        
    ##################################       PARAMETERS            #################################
    ################################################################################################
        
    model.dT=Param(within=PositiveIntegers)                         #Number of seconds in one time step

    model.P_PV=Param(model.T,within=NonNegativeReals)      #PV PMPP forecast
        
    model.ESS_Min_SoC=Param(model.N,within=PositiveReals)           #Minimum SoC of ESSs
    model.ESS_Max_SoC=Param(model.N,within=PositiveReals)           #Maximum SoC of ESSs
    model.ESS_SoC_Value=Param(model.N,within=PositiveReals)         #SoC value of ESSs at the begining of optimization horizon
    model.ESS_Capacity=Param(model.N,within=PositiveReals)          #Storage Capacity of ESSs
    model.ESS_Max_Charge_Power=Param(model.N,within=PositiveReals)  #Max Charge Power of ESSs
    model.ESS_Max_Discharge_Power=Param(model.N,within=PositiveReals)#Max Discharge Power of ESSs
    model.ESS_Charging_Eff=Param(model.N,within=PositiveReals)      #Charging efficiency of ESSs
    model.ESS_Discharging_Eff=Param(model.N,within=PositiveReals)   #Discharging efficiency of ESSs
        
    model.P_Grid_Max_Export_Power=Param(within=NonNegativeReals)    #Max active power export
    model.Q_Grid_Max_Export_Power=Param(within=NonNegativeReals)    #Max reactive power export
        
    model.PV_Inv_Max_Power=Param(within=PositiveReals)              #PV inverter capacity
           
    
    #Active and reactive power demand at each phases
    model.P_Load_R=Param(model.T,within=NonNegativeReals)           #Active power demand of R phase
    model.P_Load_S=Param(model.T,within=NonNegativeReals)           #Active power demand of S phase
    model.P_Load_T=Param(model.T,within=NonNegativeReals)           #Active power demand of T phase
    model.Q_Load_R=Param(model.T,within=Reals)                      #Reactive power demand of R phase
    model.Q_Load_S=Param(model.T,within=Reals)                      #Reactive power demand of S phase
    model.Q_Load_T=Param(model.T,within=Reals)                      #Reactive power demand of T phase
          
    ################################################################################################
        
    ##################################       VARIABLES             #################################
    ################################################################################################
    model.P_PV_R=Var(model.T,within=NonNegativeReals)       #Active power output of PV inverter's R phase
    model.P_PV_S=Var(model.T,within=NonNegativeReals)       #Active power output of PV inverter's S phase
    model.P_PV_T=Var(model.T,within=NonNegativeReals)       #Active power output of PV inverter's T phase
    model.Q_PV_R=Var(model.T,within=Reals)                  #Reactive power output of PV inverter's R phase
    model.Q_PV_S=Var(model.T,within=Reals)                  #Reactive power output of PV inverter's S phase
    model.Q_PV_T=Var(model.T,within=Reals)                  #Reactive power output of PV inverter's T phase
    
    model.P_Grid_R=Var(model.T,within=Reals)                #Active power exchange with grid at R phase
    model.P_Grid_S=Var(model.T,within=Reals)                #Active power exchange with grid at S phase
    model.P_Grid_T=Var(model.T,within=Reals)                #Active power exchange with grid at S phase
    model.Q_Grid_R=Var(model.T,within=Reals)                #Reactive power exchange with grid at R phase
    model.Q_Grid_S=Var(model.T,within=Reals)                #Reactive power exchange with grid at S phase
    model.Q_Grid_T=Var(model.T,within=Reals)                #Reactive power exchange with grid at T phase
    
    model.P_ESS_R=Var(model.N,model.T,within=Reals)         #Active power output of ESS inverter's R phase
    model.P_ESS_S=Var(model.N,model.T,within=Reals)         #Active power output of ESS inverter's S phase
    model.P_ESS_T=Var(model.N,model.T,within=Reals)         #Active power output of ESS inverter's T phase
    model.Q_ESS_R=Var(model.N,model.T,within=Reals)         #Reactive power output of ESS inverter's R phase
    model.Q_ESS_S=Var(model.N,model.T,within=Reals)         #Reactive power output of ESS inverter's S phase
    model.Q_ESS_T=Var(model.N,model.T,within=Reals)         #Reactive power output of ESS inverter's T phase
            
    model.P_PV_Output=Var(model.T,within=NonNegativeReals)#,bounds=(0,model.PV_Inv_Max_Power))            #Total active power output of PV inverter
    model.Q_PV_Output=Var(model.T,within=Reals)#,bounds=(-model.PV_Inv_Max_Power,model.PV_Inv_Max_Power)) #Total reactive power output of PV inverter
                
    model.P_Grid_Output=Var(model.T,within=Reals,bounds=(-model.P_Grid_Max_Export_Power,100000))         #Total active power exchange with grid
    model.Q_Grid_Output=Var(model.T,within=Reals,bounds=(-model.Q_Grid_Max_Export_Power,100000))         #Total reactive power exchange with grid

        
    def ESS_Power_Bounds(model,n,t):
        return (-model.ESS_Max_Charge_Power[n], model.ESS_Max_Discharge_Power[n])
    model.P_ESS_Output=Var(model.N,model.T,within=Reals)
    model.Q_ESS_Output=Var(model.N,model.T,within=Reals)
    model.S_ESS_Output = Var(model.N,model.T,within=Reals,bounds=ESS_Power_Bounds)
        
    def ESS_SOC_Bounds(model,n,t):
        return (model.ESS_Min_SoC[n], model.ESS_Max_SoC[n])
    model.SoC_ESS=Var(model.N,model.T_SoC,within=NonNegativeReals,bounds=ESS_SOC_Bounds)
        ################################################################################################
        
               
    ###########################################################################
    #######                         CONSTRAINTS                         #######

    #P load constraints
    def con_rule_Pdem_R(model,t):
        return model.P_Load_R[t]==model.P_PV_R[t]+ model.P_Grid_R[t] + sum(model.P_ESS_R[n,t] for n in model.N)
    def con_rule_Pdem_S(model,t):
        return model.P_Load_S[t]==model.P_PV_S[t]+ model.P_Grid_S[t] + sum(model.P_ESS_S[n,t] for n in model.N)
    def con_rule_Pdem_T(model,t):
        return model.P_Load_T[t]==model.P_PV_T[t]+ model.P_Grid_T[t] + sum(model.P_ESS_T[n,t] for n in model.N)
        
    #Q load constraints
    def con_rule_Qdem_R(model,t):
        return model.Q_Load_R[t]==model.Q_PV_R[t]+ model.Q_Grid_R[t] + sum(model.Q_ESS_R[n,t] for n in model.N)
    def con_rule_Qdem_S(model,t):
        return model.Q_Load_S[t]==model.Q_PV_S[t]+ model.Q_Grid_S[t] + sum(model.Q_ESS_S[n,t] for n in model.N)
    def con_rule_Qdem_T(model,t):
        return model.Q_Load_T[t]==model.Q_PV_T[t]+ model.Q_Grid_T[t] + sum(model.Q_ESS_T[n,t] for n in model.N)
        
    #PV constraints
    def con_rule_pv_P(model,t):
        return model.P_PV_Output[t]==model.P_PV_R[t]+model.P_PV_S[t]+model.P_PV_T[t]
    def con_rule_pv_Q(model,t):
        return model.Q_PV_Output[t]==model.Q_PV_R[t]+model.Q_PV_S[t]+model.Q_PV_T[t]
    def con_rule_pv_potential(model,t):
        return model.P_PV_Output[t]*model.P_PV_Output[t]+model.Q_PV_Output[t]*model.Q_PV_Output[t]<= model.P_PV[t]*model.P_PV[t]
    def con_rule_pv_inverter(model,t):
        return  model.P_PV_Output[t]*model.P_PV_Output[t]+model.Q_PV_Output[t]*model.Q_PV_Output[t]<= model.PV_Inv_Max_Power*model.PV_Inv_Max_Power
                
    #Import/Export constraints
    def con_rule_grid_P(model,t):
        return model.P_Grid_Output[t]==model.P_Grid_R[t]+model.P_Grid_S[t]+model.P_Grid_T[t]
    def con_rule_grid_Q(model,t):
        return model.Q_Grid_Output[t]==model.Q_Grid_R[t]+model.Q_Grid_S[t]+model.Q_Grid_T[t]
    
    #SoC constraints
    def con_rule_ess_P(model,n,t):
        return model.P_ESS_Output[n,t]==model.P_ESS_R[n,t]+model.P_ESS_S[n,t]+model.P_ESS_T[n,t]
    def con_rule_ess_Q(model,n,t):
        return model.Q_ESS_Output[n,t]==model.Q_ESS_R[n,t]+model.Q_ESS_S[n,t]+model.Q_ESS_T[n,t]
    def con_rule_ess_S(model,n,t):
        return model.S_ESS_Output[n,t]*model.S_ESS_Output[n,t]==model.P_ESS_Output[n,t]*model.P_ESS_Output[n,t]+model.Q_ESS_Output[n,t]*model.Q_ESS_Output[n,t]
         
    def con_rule_socBalance(model,n,t):
        return model.SoC_ESS[n,t+1]==model.SoC_ESS[n,t] - model.S_ESS_Output[n,t]*model.dT/model.ESS_Capacity[n]
    def con_rule_iniSoC(model,n):
        return model.SoC_ESS[n,0]==model.ESS_SoC_Value[n]
       
    model.con_Pdem_R=Constraint(model.T,rule=con_rule_Pdem_R)
    model.con_Pdem_S=Constraint(model.T,rule=con_rule_Pdem_S)
    model.con_Pdem_T=Constraint(model.T,rule=con_rule_Pdem_T)
    model.con_Qdem_R=Constraint(model.T,rule=con_rule_Qdem_R)
    model.con_Qdem_S=Constraint(model.T,rule=con_rule_Qdem_S)
    model.con_Qdem_T=Constraint(model.T,rule=con_rule_Qdem_T)
        
    model.con_pv_P=Constraint(model.T,rule=con_rule_pv_P)
    model.con_pv_Q=Constraint(model.T,rule=con_rule_pv_Q)
    model.con_pv_pmax=Constraint(model.T,rule=con_rule_pv_potential)
    model.con_pv_inv=Constraint(model.T,rule=con_rule_pv_inverter)
        
    model.con_grid_P=Constraint(model.T,rule=con_rule_grid_P)
    model.con_grid_Q=Constraint(model.T,rule=con_rule_grid_Q)
        
    model.con_ess_P=Constraint(model.N,model.T,rule=con_rule_ess_P)
    model.con_ess_Q=Constraint(model.N,model.T,rule=con_rule_ess_Q)
    model.con_ess_S=Constraint(model.N,model.T,rule=con_rule_ess_S)
    model.con_ess_soc=Constraint(model.N,model.T,rule=con_rule_socBalance)
    model.con_ess_Inisoc=Constraint(model.N,rule=con_rule_iniSoC)
        
    ###########################################################################
    #######                         OBJECTIVE                           #######
    ###########################################################################
    def obj_rule(model):
        return sum(model.P_PV[t]*model.P_PV[t]-model.P_PV_Output[t]*model.P_PV_Output[t]-model.Q_PV_Output[t]*model.Q_PV_Output[t] for t in model.T)
    model.obj=Objective(rule=obj_rule, sense = minimize)

    #self.model=model
    
