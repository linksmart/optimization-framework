# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""

from pyomo.environ import SolverFactory
import optimization.models as models
import os, logging
import importlib
import importlib.util
#from optimization.models.ReferenceModel import Model

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class OptController:

    def __init__(self, object_name,solver_name,data_path, model_path):
        logger.info("Initializing optimization controller")


        #Loading variables
        self.name = object_name
        self.results=""
        self.model_path = model_path
        self.data_path = data_path
        self.solver_name = solver_name

        try:
            #dynamic load of a class
            logger.info("This is the model path: "+self.model_path)
            module = self.path_import2(self.model_path)
            logger.info(getattr(module,'Model'))
            self.my_class = getattr(module,'Model')

        except Exception as e:
            logger.error(e)


    # Importint a class dynamically
    def path_import2(self,absolute_path):
        spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
        module = spec.loader.load_module(spec.name)
        return module


    #Start the optimization process and gives back a result
    def start(self):

        logger.info("Starting optimization controller")
        #Takimg the mathematical model from the configuration file

        try:
            #Creating an optimization instance with the referenced model
            #from optimization.models.ReferenceModel import Model
            instance = self.my_class.model.create_instance(self.data_path)
            # instance.pprint()

            opt = SolverFactory(self.solver_name)
            self.results = opt.solve(instance)
            return self.results
        except Exception as e:
            logger.error(e)
            return e


