# -*- coding: utf-8 -*-
"""
Created on Tue Jul 31 14:22:24 2018

@author: guemruekcue
"""

import csv

def import_statistics(sourcefile,starttime,maxNbOfCars):  
    #Returns a dictionary
    #keys are (time,iniState,finState)
    #time:timestep
    statistics1={}
    statistics2={}
    
    with open(sourcefile, newline='') as myFile:  
        reader = csv.reader(myFile)
        rw_nb=0
        for row in reader:
            ts=rw_nb//(maxNbOfCars+1)
            statistics1[ts,int(row[1])]=float(row[2])
            rw_nb+=1
            
            if row[0]==starttime:
                listTop=ts
                
                
    for tS,nbHomeCars in sorted(statistics1.keys()):
        
        if tS-listTop>=0:            
            statistics2[tS-listTop,nbHomeCars]=statistics1[tS,nbHomeCars]
        else:
            statistics2[tS-listTop+int(len(statistics1.keys())/maxNbOfCars),nbHomeCars]=statistics1[tS,nbHomeCars]   
 
    return statistics2

"""
import os
AllAproaches_dir=os.path.dirname(os.path.dirname(__file__))
Inputs_dir=os.path.join(AllAproaches_dir,'Inputs')
Forecast_inp=Inputs_dir+'\Forecasts_60M.xlsx'
Behavior_inp=Inputs_dir+'\PMFs_60M.csv'

behavMod=import_statistics(Behavior_inp,"00:00",7)
"""