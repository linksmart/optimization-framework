"""
Created on Mai 23 11:21 2019

@author: nishit
"""
import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class ModelDerivedParameters:

    @staticmethod
    def get_derived_parameter_mapping(model_name):
        base, derived = [], []
        if model_name == "CarParkModel" or model_name == "CarParkModel2":
            base, derived = ModelDerivedParameters.car_park_model()
        if model_name == "StochasticResidentialMaxPV":
            base, derived = ModelDerivedParameters.car_park_model()
        return base, derived

    @staticmethod
    def car_park_model():
        base = []
        derived = ['Value', 'Initial_ESS_SoC', 'Initial_VAC_SoC', 'Number_of_Parked_Cars', 'VAC_Capacity',
                   'Behavior_Model', 'VAC_SoC_Value', 'Feasible_ESS_Decisions', 'Feasible_VAC_Decisions', 'Value_Index',
                   'Behavior_Model_Index', 'Timestep']
        return base, derived
