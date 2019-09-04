"""
Created on Mai 23 11:21 2019

@author: nishit
"""
from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class ModelDerivedParameters:

    @staticmethod
    def get_derived_parameter_mapping(model_name):
        base, derived = [], []
        if model_name == "CarParkModel" or model_name == "CarParkModel2" or "CarPark" in model_name:
            base, derived = ModelDerivedParameters.car_park_model()
        if model_name in ["StochasticResidentialMaxPV","StochasticResidentialMinGrid","StochasticResidentialMinPBill"]:
            base, derived = ModelDerivedParameters.car_park_model()
        return base, derived

    @staticmethod
    def car_park_model():
        base = []
        derived = ['Value', 'Initial_ESS_SoC', 'Initial_VAC_SoC', 'Number_of_Parked_Cars', 'VAC_Capacity',
                   'Behavior_Model', 'VAC_SoC_Value', 'Feasible_ESS_Decisions', 'Feasible_VAC_Decisions', 'Value_Index',
                   'Behavior_Model_Index', 'Timestep', "VAC_States_Min", "Recharge", "final_ev_soc"]
        return base, derived
