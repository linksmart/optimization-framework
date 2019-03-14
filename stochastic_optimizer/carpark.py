# -*- coding: utf-8 -*-
"""
Created on Fri Aug 17 19:26:15 2018

@author: guemruekcue
"""

from itertools import product


class Charger():
    
    def __init__(self,kW):
        self.kW=kW
        self.hostedCar=None
        
    def plug(self,car):
        self.hostedCar=car
        self.plugged=1
        
    def unplug(self):
        self.hostedCar=None       
        self.plugged=0
        
    def charge(self,chargePeriod,chargePower):
        
        if self.plugged==1:
            self.hostedCar.charge(chargePeriod,chargePower)
        else:
            print("Charge decision cannot be implemented")


class Car():
    
    def __init__(self,batteryCapacity):
        self.batteryCapacity=batteryCapacity*3600
        
    def setSoC(self,soc):
        self.soc=soc
    
    def charge(self,chargePeriod,chargePower):
        self.soc=self.soc+chargePower*chargePeriod/self.batteryCapacity    
    
    
class CarPark():
    
    def __init__(self,chargerList,carList):
        
        self.cars={}
        self.chargers={}
        
        chargerIndex=1
        carIndex=1
        for charger in chargerList:
            self.chargers[chargerIndex]=charger
            chargerIndex+=1

        self.vac_capacity=0                
        for car in carList:
            self.cars[carIndex]=car
            self.vac_capacity+=car.batteryCapacity
            carIndex+=1
        
        self.carNb=len(self.cars)

    def maxChargePowerCalculator(self,chargingperiod):
        """
        Returns a dictionary "connections"
            keys: charger labels 
            values: max charging power input to the connected car
        """
             
        connections={}
        for key,charger in self.chargers.items():          
            if charger.hostedCar!=None:
                car=charger.hostedCar
                batteryDoD=(1-car.soc)*car.batteryCapacity   #kW-sec
                
                chargerLimit=charger.kW
                carLimit=batteryDoD/chargingperiod
        
                connections[key]=min(chargerLimit,carLimit)
            
        return connections
            

