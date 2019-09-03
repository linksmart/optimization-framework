# -*- coding: utf-8 -*-
"""
Created on Tue Jul 31 14:22:24 2018

@author: guemruekcue
"""

import csv

def import_statistics(sourcefile,starttime):  
    """
    Forms a dictionary for MarkovModel from the source csv file
    
    input
    --------
    sourcefile: Source csv file for Markov Model
    starttime : For which hour the optimization is run   
    
    Returns a dictionary statistics2
    keys are (time,iniState,finState)
    time:timestep
    """
    

    statistics1={}
    statistics2={}
    
    with open(sourcefile, newline='') as myFile:  
        reader = csv.reader(myFile)
        rw_nb=0
        for row in reader:
            ts=rw_nb//4
            statistics1[ts,int(row[1]),int(row[2])]=float(row[3])
            rw_nb+=1
            
            if row[0]==starttime:
                listTop=ts
                
                
    for tS,ini,fin in sorted(statistics1.keys()):
        
        if tS-listTop>=0:            
            statistics2[tS-listTop,ini,fin]=statistics1[tS,ini,fin]
        else:
            statistics2[tS-listTop+int(len(statistics1.keys())/4),ini,fin]=statistics1[tS,ini,fin]   
    
    return statistics2
