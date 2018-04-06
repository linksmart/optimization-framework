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

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class OptController:

    def __init__(self, object_name,solver_name,data_path, model_name):
        logger.info("Initializing optimization controller")


        #Loading variables
        self.name = object_name
        self.results=""
        self.model_name = model_name
        self.data_path = data_path
        self.solver_name = solver_name
        #print("Problem solved with: " + solver_name)

    # New way of importing
    def path_import2(absolute_path):
        spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
        module = spec.loader.load_module(spec.name)
        return module

    """ 
    Start the optimization process and gives back a result
    """

    def start(self):


        logger.info("Starting optimization controller")
        #Takimg the mathematical model from the configuration file

        try:
            module = self.path_import2("/usr/src/app/optimization/models/model_1.py")
        except Exception as e:
            logger.error(e)

        from optimization.models.ReferenceModel import model

        #Creating an optimization instance with the referenced model
        instance = model.create_instance(self.data_path)
        # instance.pprint()


        opt = SolverFactory(self.solver_name)
        self.results = opt.solve(instance)

        #self.results = "hola"
        return self.results
