# -*- coding: utf-8 -*-
"""
Created on Wed Apr 25 16:48:49 2018

@author: guemruekcue
"""

#Minimum grid exchange with 0.1 SOC discretization
from ScenarioClass import scenario_24Ts
from DynamicProgram import StochasticDynamicProgram
from pyomo.environ import SolverFactory
import time
import os

# %%
pbmatrix='MarkovModel.csv'
pbmatrix2='EVSoCModel.csv'

prob_plug={}
with open(pbmatrix) as f:
    for line in f:
        row=line.split(",")
        prob_plug[int(row[0]),int(row[1]),int(row[2])]=float(row[3])        

prob_end_soc={}
with open(pbmatrix2) as f2:
    for line in f2:
        row=line.split(",")
        prob_end_soc[int(row[0])]=float(row[1])   


# %%
opt1=SolverFactory('glpk',executable="/usr/local/bin/glpsol")
opt2= SolverFactory("ipopt", executable="/usr/src/app/share/CoinIpopt/build/bin/ipopt")
opt3= SolverFactory("bonmin", executable="/usr/src/app/share/CoinBonmin/build/bin/bonmin")

ess_domain=[20,30,40,50,60,70,80,90,100]
ev_domain=[0,10,20,30,40,50,60,70]


dynprog=StochasticDynamicProgram(scenario_24Ts,ess_domain,ev_domain,opt3,0,prob_plug,prob_end_soc)


start_time=time.time()
dynprog.wholeMapCalculation()
end_time=time.time()
print("Execution completed in",end_time-start_time,"seconds")
      
# %%  
Decision=dynprog.Decision
Value=dynprog.Value


P_Grid_Output  =[]
P_PV_Output    =[]
P_ESS_Output   =[]
P_EV_ChargeHome=[]
ess_SoC_record=[]
ev_SoC_record=[]

Position=dict.fromkeys(range(24),1)
for ts in range(7,21):
    Position[ts]=0

EV_expected=40

for ts in range(24):
    if ts==0:
        essSoc=40
        evSoc=30

    results=dynprog.findoptimalValues(ts,essSoc,evSoc,Position[ts])   
    P_PV_Output.append(results[0])
    P_ESS_Output.append(results[1])
    P_Grid_Output.append(results[2])
    P_EV_ChargeHome.append(results[3])
    
    essSoc=min(ess_domain, key=lambda x:abs(x-results[4]))
    evSoc=min(ev_domain, key=lambda x:abs(x-results[5])) if Position[ts]==1 else EV_expected

    ess_SoC_record.append(essSoc)
    ev_SoC_record.append(evSoc)


