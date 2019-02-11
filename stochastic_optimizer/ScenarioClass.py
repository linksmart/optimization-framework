# -*- coding: utf-8 -*-
"""
Created on Fri Apr 20 16:46:27 2018

@author: guemruekcue
"""

class Scenario():
    
    def __init__(self,T,PV_Inv_Max_Power,P_Grid_Max_Export_Power,
                 ESS_Min_SoC,ESS_Max_SoC,ESS_Capacity,ESS_Max_Charge_Power,ESS_Max_Discharge_Power,
                 EV_Min_SoC,EV_Max_SoC,EV_Capacity,EV_Max_Charge_Power,EV_Max_Drive_Power,
                 P_Load_Forecast,P_PV_Forecast):
        
        # Time parameters
        self.T=T  #Total number of time steps: Optimization horizon
        
        #Time invariant parameters
        self.PV_Inv_Max_Power       =PV_Inv_Max_Power
        self.P_Grid_Max_Export_Power=P_Grid_Max_Export_Power
        self.ESS_Min_SoC            =ESS_Min_SoC
        self.ESS_Max_SoC            =ESS_Max_SoC
        self.ESS_Capacity           =ESS_Capacity
        self.ESS_Max_Charge_Power   =ESS_Max_Charge_Power
        self.ESS_Max_Discharge_Power=ESS_Max_Discharge_Power
        self.EV_Min_SoC             =EV_Min_SoC
        self.EV_Max_SoC             =EV_Max_SoC
        self.EV_Capacity            =EV_Capacity
        self.EV_Max_Charge_Power    =EV_Max_Charge_Power
        self.EV_Max_Drive_Power     =EV_Max_Drive_Power
        
        #Forecasts
        self.P_Load_Forecast =P_Load_Forecast
        self.P_PV_Forecast   =P_PV_Forecast
        

# %% A scenario
p_Load_Forecast={0:   0.057,
                 1:   0.0906,
                 2:   0.0906,
                 3:   0.070066667,
                 4:	0.077533333,
                 5:	0.0906,
                 6:	0.0906,
                 7:	0.10935,
                 8:	0.38135,
                 9:	1.473716667,
                 10:	0.988183333,
                 11:	2.4413,
                 12:	0.4216,
                 13:	0.21725,
                 14:	0.4536,
                 15:	0.4899,
                 16:	0.092466667,
                 17:	0.088733333,
                 18:	0.0906,
                 19:	0.47475,
                 20:	0.48255,
                 21:	1.051866667,
                 22:	1.296316667,
                 23:	0.200733333}

p_PV_Forecast={  0:   0,
                 1:	0,
                 2:	0,
                 3:	0,
                 4:	0,
                 5:	0,
                 6:	0,
                 7:	0,
                 8:	1.13248512,
                 9:	3.016735616,
                 10:	4.823979947,
                 11:	6.329861639,
                 12:	7.06663104,
                 13:	7.42742784,
                 14:	7.420178035,
                 15:	7.077290784,
                 16:	5.99361984,
                 17:	4.036273408,
                 18:	1.462618829,
                 19:	0,
                 20:	0,
                 21:	0,
                 22:	0,
                 23:	0} 

pv_Inv_Max_Power          = 10.0;
p_Grid_Max_Export_Power   = 10.0;
ess_Min_SoC               = int(0.25*100);
ess_Max_SoC               = int(0.95*100);
ess_Capacity              = 10.0;   #kWh
ess_Max_Charge_Power      = 3.0;   #kW
ess_Max_Discharge_Power   = 3.0;   #kW
ev_Min_SoC                = int(0.20*100);
ev_Max_SoC                = int(1.00*100);
ev_Capacity               = 30.0;   #kWh
ev_Max_Charge_Power      = 3.0;   #kW
ev_Max_Drive_Power      = 5.0;   #kW
horizon=24;   


# %% optimization model for the calculation of optimal decision at a particular state
scenario_24Ts=Scenario(horizon,pv_Inv_Max_Power,p_Grid_Max_Export_Power,
                 ess_Min_SoC,ess_Max_SoC,ess_Capacity,ess_Max_Charge_Power,ess_Max_Discharge_Power,
                 ev_Min_SoC,ev_Max_SoC,ev_Capacity,ev_Max_Charge_Power,ev_Max_Drive_Power,
                 p_Load_Forecast,p_PV_Forecast)


