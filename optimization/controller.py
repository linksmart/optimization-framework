# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""


import optimization.models as models
import os, logging
import importlib
import importlib.util
import threading
from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.opt.parallel import SolverManagerFactory
from pyomo.opt import SolverStatus, TerminationCondition
import subprocess
import time
#from objdict import ObjDict
from IO.outputController import OutputController



#from optimization.models.ReferenceModel import Model

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class OptController(threading.Thread):

    def __init__(self, object_name,solver_name,data_path, model_path, time_step,output_config):
        #threading.Thread.__init__(self)
        super(OptController,self).__init__()
        logger.info("Initializing optimization controller")
        #Loading variables
        self.name = object_name
        self.results=""
        self.model_path = model_path
        self.data_path = data_path
        self.solver_name = solver_name
        self.time_step=time_step
        self.output_config=output_config

        self.stopRequest=threading.Event()

        try:
            #dynamic load of a class
            logger.info("This is the model path: "+self.model_path)
            module = self.path_import2(self.model_path)
            logger.info(getattr(module,'Model'))
            self.my_class = getattr(module,'Model')

        except Exception as e:
            logger.error(e)

        self.output = OutputController(self.output_config)

    # Importint a class dynamically
    def path_import2(self,absolute_path):
        spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
        module = spec.loader.load_module(spec.name)
        return module

    def join(self, timeout=None):
        self.stopRequest.set()
        super(OptController, self).join(timeout)

    def Stop(self):
        #
        if self.isAlive():
            self.join()


    #Start the optimization process and gives back a result
    def run(self):
        logger.info("Starting optimization controller")

        ###Starts name server, dispatcher server and pyro_mip_server
        name_server=subprocess.Popen(["/usr/local/bin/pyomo_ns"])
        dispatch_server=subprocess.Popen(["/usr/local/bin/dispatch_srvr"])
        pyro_mip_server=subprocess.Popen(["/usr/local/bin/pyro_mip_server"])

        try:
            ###maps action handles to instances
            action_handle_map={}

            #####create a solver
            optsolver = SolverFactory(self.solver_name)
            logger.info("solver instantiated")

            ###create a solver manager
            solver_manager=SolverManagerFactory('pyro')
            if solver_manager is None:
                logger.error("Failed to create a solver manager")

            key_P_PV_Potential = 'P_PV_Potential'
            key_Q_PV_Output = 'Q_PV_Output'
            key_P_ESS_Output = 'P_ESS_Output'
            key_P_Grid_Output = 'P_Grid_Output'
            key_Q_Grid_Output = 'Q_Grid_Output'
            key_P_EV_Output= 'P_EV_Output'
            key_SoC_ESS = 'SoC_ESS'
            key_Soc_EV = 'Soc_EV'

            while not self.stopRequest.isSet():
                # Creating an optimization instance with the referenced model
                instance = self.my_class.model.create_instance(self.data_path)
                logger.info("Instance created with pyomo")

                #logger.info(instance.pprint())

                action_handle = solver_manager.queue(instance, opt=optsolver)
                action_handle_map[action_handle] = "myOptimizationModel_1"

                ###retrieve the solutions
                for i in range(1):
                    this_action_handle=solver_manager.wait_any()
                    self.solved_name=action_handle_map[this_action_handle]
                    self.results=solver_manager.get_results(this_action_handle)


                #logger.info("The solver returned a status of:" + str(self.results.Solution.Status))

                ####Test getting constraints
                #logger.info("Constraints")
                #from pyomo.core import Constraint
                #for c in instance.component_objects(Constraint, active=True):
                    #logger.info("Constraint: ",c)
                    #cobject=getattr(instance,str(c))
                    #for index in cobject:
                        #print("      ", index, instance.dual[cobject[index]])

                ###   Testing solver status and termination condition


                if (self.results.solver.status == SolverStatus.ok) and (self.results.solver.termination_condition == TerminationCondition.optimal):
                    # this is feasible and optimal
                    logger.info("Solver status and termination condition ok")
                    logger.debug("Results for " + self.solved_name)
                    logger.debug(self.results)
                    instance.solutions.load_from(self.results)
                    try:
                        my_dict={}
                        for v in instance.component_objects(Var, active=True):
                            #logger.info("Variable: "+ str(v))
                            varobject = getattr(instance, str(v))
                            #if str(v) == "P_PV_Output":
                                #logger.info("Este es P_PV_Output")
                                #my_dict[str(v)]='2'
                                #logger.info("A ver "+ str(my_dict))
                            for index in varobject:
                                #logger.info(str(index)+", "+ str(varobject[index].value))
                                if index==0:
                                    #logger.info("Estoy aqui")
                                    #logger.info(str(index) + ", " + str(varobject[index].value))

                                    list=[{index,varobject[index].value}]
                                    #logger.info("Estaes la lista"+str(list))
                                    try:
                                        # Try and add to the dictionary by key ref
                                        my_dict[str(v)]=list

                                    except KeyError:
                                        # Append new index to currently existing items
                                        my_dict = {**my_dict, **{v: list}}


                        #logger.info("Este es mi dict"+str(my_dict))
                        #logger.debug("This is the output data: " + str(self.output_config))
                        self.output.publishController(my_dict)
                    except Exception as e:
                        logger.error(e)
                elif self.results.solver.termination_condition == TerminationCondition.infeasible:
                    # do something about it? or exit?
                    logger.info("Termination condition is infeasible")
                else:
                    # something else is wrong
                    #print(self.results.solver)
                    logger.info("Nothing fits")

                logger.info("Optimization thread going to sleep for "+self.time_step+" seconds")
                time.sleep(self.time_step)

            #If Stop signal arrives it tries to disconnect all mqtt clients
            for key,object in self.output.mqtt.items():
                object.MQTTExit()
                logger.debug("Client "+key+" is being disconnected")
            ###close subprocesses


        except Exception as e:
            logger.error(e)
            return e


