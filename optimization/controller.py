# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""

import importlib.util
import json
import threading
import pprint

from itertools import product
import os
import pandas as pd
from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.opt.parallel import SolverManagerFactory
from pyomo.opt import SolverStatus, TerminationCondition
import subprocess
import time

from IO.MQTTClient import InvalidMQTTHostException
from pyutilib.pyro import shutdown_pyro_components

from IO.inputController import InputController
from IO.outputController import OutputController
from IO.redisDB import RedisDB
from optimization.ModelException import InvalidModelException
import logging
from threading import Event
from optimization.functions import import_statistics
from optimization.carpark import CarPark, Charger, Car

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class OptController(threading.Thread):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds):
        # threading.Thread.__init__(self)
        super(OptController, self).__init__()
        logger.info("Initializing optimization controller")
        # Loading variables
        self.id = id
        self.results = ""
        self.model_path = model_path
        self.solver_name = solver_name
        self.control_frequency = control_frequency
        self.repetition = repetition
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.output_config = output_config
        self.input_config_parser = input_config_parser
        self.stopRequest = threading.Event()
        self.finish_status = False
        self.redisDB = RedisDB()
        self.lock_key = "id_lock"

        try:
            # dynamic load of a class
            logger.info("This is the model path: " + self.model_path)
            module = self.path_import2(self.model_path)
            logger.info(getattr(module, 'Model'))
            self.my_class = getattr(module, 'Model')

        except Exception as e:
            logger.error(e)
            raise InvalidModelException("model is invalid/contains python syntax errors")

        if "False" in self.redisDB.get("Error mqtt"+self.id):
            self.output = OutputController(self.id, self.output_config)
        if "False" in self.redisDB.get("Error mqtt" + self.id):
            self.input = InputController(self.id, self.input_config_parser, config, self.control_frequency,
                                         self.horizon_in_steps, self.dT_in_seconds)

    # Importint a class dynamically
    def path_import2(self, absolute_path):
        spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
        module = spec.loader.load_module(spec.name)
        return module

    def join(self, timeout=None):
        self.stopRequest.set()
        super(OptController, self).join(timeout)

    def Stop(self):
        try:
            self.input.Stop()
        except Exception as e:
            logger.error("error stopping input " + str(e))
        try:
            self.output.Stop()
        except Exception as e:
            logger.error("error stopping output " + str(e))
        if self.isAlive():
            self.join(1)

    def update_count(self):
        st = time.time()
        if self.repetition > 0:
            path = "/usr/src/app/utils/ids_status.txt"
            if os.path.exists(path):
                try:
                    if self.redisDB.get_lock(self.lock_key, self.id):
                        data = []
                        with open(path, "r") as f:
                            data = f.readlines()
                        if len(data) > 0:
                            line = None
                            for s in data:
                                if self.id in s and "repetition\": -1" not in s:
                                    line = s
                                    break
                            if line is not None:
                                i = data.index(line)
                                line = json.loads(line.replace("\n", ""))
                                line["repetition"] -= 1
                                data[i] = json.dumps(line, sort_keys=True, separators=(', ', ': ')) + "\n"
                                with open(path, "w") as f:
                                    f.writelines(data)
                except Exception as e:
                    logging.error("error updating count in file " + str(e))
                finally:
                    self.redisDB.release_lock(self.lock_key, self.id)
        st = int(time.time() - st)
        return st

    # Start the optimization process and gives back a result
    def run(self):
        logger.info("Starting optimization controller")
        solver_manager = None
        return_msg = "success"
        try:
            # maps action handles to instances
            action_handle_map = {}

            # create a solver
            optsolver = SolverFactory(self.solver_name)
            logger.debug("Solver factory: " + str(optsolver))
            # optsolver.options["max_iter"]=5000
            logger.info("solver instantiated with " + self.solver_name)

            # create a solver manager
            solver_manager = SolverManagerFactory('pyro')

            if solver_manager is None:
                logger.error("Failed to create a solver manager")
            else:
                logger.debug("Solver manager created: " + str(solver_manager) + str(type(solver_manager)))

            count = 0
            logger.info("This is the id: " + self.id)
            while not self.stopRequest.isSet():
                logger.info("waiting for data")
                data_dict = self.input.get_data()  # blocking call

                if self.stopRequest.isSet():
                    break

                ######################################
                # STOCHASTIC OPTIMIZATION

                # Inputs
                charger1 = Charger(6)
                charger2 = Charger(6)
                charger3 = Charger(6)
                charger4 = Charger(6)
                charger5 = Charger(6)
                charger6 = Charger(6)
                charger7 = Charger(6)
                chargers = [charger1, charger2, charger3, charger4, charger5, charger6, charger7]
                car1 = Car(30)
                car2 = Car(30)
                car3 = Car(30)
                car4 = Car(30)
                car5 = Car(30)
                car6 = Car(30)
                car7 = Car(30)
                car1.setSoC(0.5)
                car2.setSoC(0.5)
                car3.setSoC(0.5)
                car4.setSoC(0.5)
                car5.setSoC(0.5)
                car6.setSoC(0.5)
                car7.setSoC(0.5)
                charger1.plug(car1)
                charger2.plug(car2)
                charger3.plug(car3)
                cars = [car1, car2, car3, car4, car5, car6, car7]
                mycarpark = CarPark(chargers, cars)

                Forecast_inp = '/usr/src/app/stochastic_optimizer/Forecasts_60M.xlsx'
                Behavior_inp = '/usr/src/app/stochastic_optimizer/PMFs_60M.csv'
                xl = pd.ExcelFile(Forecast_inp)
                forecasts = xl.parse("0")
                behavMod = import_statistics(Behavior_inp, "00:00", 7)

                forecast_pv = dict(enumerate(forecasts['PV'].values.tolist()))
                forecast_price = dict(enumerate(forecasts['Price'].values.tolist()))

                ess_soc_states = range(0, 110, 10)
                ess_decision_domain = range(-10, 20, 10)
                vac_soc_states = [x * 0.1 for x in range(0, 1025, 25)]  # np.linspace(0,100.0,2.5,endpoint=True)
                vac_decision_domain = [x * 0.1 for x in range(0, 225, 25)]  # np.linspace(0.0,20.0,2.5,endpoint=True)

                T = self.horizon_in_steps

                #Initialize empty lookup tables
                keylistforValue    =[(t,s_ess,s_vac) for t,s_ess,s_vac in product(list(range(0,T+1)),ess_soc_states,vac_soc_states)]
                keylistforDecisions=[(t,s_ess,s_vac) for t,s_ess,s_vac in product(list(range(0,T)),ess_soc_states,vac_soc_states)]
                
                Value   =dict.fromkeys(keylistforValue)
                Decision=dict.fromkeys(keylistforDecisions)
            
                for t,s_ess,s_vac in product(range(0,T),ess_soc_states,vac_soc_states):
                    Decision[t,s_ess,s_vac]={'PV':None,'Grid':None,'ESS':None,'VAC':None}
                    Value[t,s_ess,s_vac]=None

                for s_ess,s_vac in product(ess_soc_states,vac_soc_states):
                    Value[T,s_ess,s_vac]=1.0


                ##### Enter Data into data_dict


                data_dict[None]["Number_of_Parked_Cars"] = { None: mycarpark.carNb }
                data_dict[None]["VAC_Capacity"] = { None: mycarpark.vac_capacity }

                ess_capacity = 0.675*3600
                data_dict[None]["ESS_Capacity"] = { None: ess_capacity }

                stochastic_start_time = time.time()
                    
                    
                for timestep in reversed(range(0, self.horizon_in_steps)):
                    logger.info(f"Timestep :#{timestep}")

                    instance_id = 0

                    for ini_ess_soc, ini_vac_soc in product(ess_soc_states, vac_soc_states):

                        feasible_Pess=[]            #Feasible charge powers to ESS under the given conditions
                        for p_ESS in ess_decision_domain:  #When decided charging with p_ESS
                            if min(ess_soc_states)<=p_ESS+ini_ess_soc<=max(ess_soc_states): #if the final ess_SoC is within the specified domain 
                                feasible_Pess.append(p_ESS)  

                        feasible_Pvac=[]            #Feasible charge powers to VAC under the given conditions
                        for p_VAC in vac_decision_domain:         #When decided charging with p_VAC   
                            if p_VAC+ini_vac_soc<=max(vac_soc_states): #if the final vac_SoC is within the specified domain
                                feasible_Pvac.append(p_VAC)

                        data_dict[None]["Feasible_ESS_Decisions"] = { None: feasible_Pess }
                        data_dict[None]["Feasible_VAC_Decisions"] = { None: feasible_Pvac }

                        data_dict[None]["Initial_ESS_SoC"] = { None: ini_ess_soc }
                        data_dict[None]["Initial_VAC_SoC"] = { None: ini_vac_soc }

                        bm_idx = [ key[1] for key in behavMod.keys() if key[0] == timestep]
                        bm = { key[1]: value for key, value in behavMod.items() if key[0] == timestep }

                        data_dict[None]["Behavior_Model_Index"] = { None: bm_idx }
                        data_dict[None]["Behavior_Model"] = bm


                        value_index = [ (s_ess,s_vac) for t,s_ess,s_vac in Value.keys() if t == timestep+1]
                        data_dict[None]["Value_Index"] = { None: value_index }

                        value = { v:Value[timestep+1, v[0], v[1] ] for v in value_index }
                        data_dict[None]["Value"] = value


                        data_dict[None]["P_PV_Forecast"] = { None: forecast_pv[timestep] }

                        # * Create Optimization instance

                        # Creating an optimization instance with the referenced model
                        try:
                            logger.debug("Creating an optimization instance")
                            instance = self.my_class.model.create_instance(data_dict)
                        except Exception as e:
                            logger.error("Error creating instance")
                            logger.error(e)
                        # instance = self.my_class.model.create_instance(self.data_path)
                        # logger.info("Instance created with pyomo")

                        # * Queue the optimization instance

                        try:
                            # logger.info(instance.pprint())
                            action_handle = solver_manager.queue(instance, opt=optsolver)
                            # logger.debug("Solver queue created " + str(action_handle))
                            logger.debug("solver queue actions = " + str(solver_manager.num_queued()))
                            action_handle_map[action_handle] = "Instance:"+str(instance_id)
                            # logger.debug("Action handle map: " + str(action_handle_map))
                            # start_time = time.time()
                            # logger.debug("Optimization starting time: " + str(start_time))
                        except Exception as e:
                            logger.error("exception "+str(e))

                        instance_id += 1

                    time.sleep(10)


                    # * Run the solver

                    results = []
                    # retrieve the solutions
                    for i in range(instance_id):
                        this_action_handle = solver_manager.wait_any()
                        result = solver_manager.get_results(this_action_handle)
                        # logger.debug("solver queue actions = " + str(solver_manager.num_queued()))
                        if this_action_handle in action_handle_map.keys():
                            self.solved_name = action_handle_map.pop(this_action_handle)
                        else:
                            self.solved_name = None
                        print("Result of instance : " + str(i))
                        # print(result)
                        results.append(result)

                    # * Check whether it is solved

                    time.sleep(10)

                    for result in results:
                        # start_time = time.time() - start_time
                        # logger.info("Time to run optimizer = " https://pyomo.readthedocs.io+ str(start_time) + " sec.")
                        if (result.solver.status == SolverStatus.ok) and (
                                result.solver.termination_condition == TerminationCondition.optimal):
                            # this is feasible and optimal
                            logger.info("Solver status and termination condition ok")
                            logger.debug("Results for " + self.solved_name + " with id: " + str(self.id))
                            # logger.debug(result)
                            instance.solutions.load_from(result)

                            # * if solved get the values in dict

                            try:
                                my_dict = {}
                                for v in instance.component_objects(Var, active=True):
                                    logger.debug("Variable in the optimization: " + str(v))
                                    varobject = getattr(instance, str(v))
                                    var_list = []
                                    try:
                                        # Try and add to the dictionary by key ref
                                        for index in varobject:
                                            var_list.append(varobject[index].value)
                                        logger.debug("Identified variables " + str(var_list))
                                        my_dict[str(v)] = var_list
                                    except Exception as e:
                                        logger.error(e)
                                

                                Decision[timestep, ini_ess_soc, ini_vac_soc]['Grid'] = my_dict["P_GRID"][0]
                                Decision[timestep, ini_ess_soc, ini_vac_soc]['PV'] = my_dict["P_PV"][0]
                                Decision[timestep, ini_ess_soc, ini_vac_soc]['ESS'] = -my_dict["P_ESS"][0]
                                Decision[timestep, ini_ess_soc, ini_vac_soc]['VAC'] = -my_dict["P_VAC"][0]

                                Value[timestep, ini_ess_soc, ini_vac_soc] = my_dict["P_PV"][0]

                                logger.info("Done".center(80,"#"))
                                logger.info(f"Timestep :#{timestep} : {ini_ess_soc}, {ini_vac_soc} ")
                                logger.info("#"*80)

                                time.sleep(2)

                                # self.output.publish_data(self.id, my_dict)
                            except Exception as e:
                                logger.error(e)
                        elif result.solver.termination_condition == TerminationCondition.infeasible:
                            # do something about it? or exit?
                            logger.info("Termination condition is infeasible")
                        else:
                            logger.info("Nothing fits")


                initial_ess_soc_value = 50
                initial_vac_soc_value = 50

                p_pv=Decision[0,initial_ess_soc_value,initial_vac_soc_value]['PV']
                p_grid=Decision[0,initial_ess_soc_value,initial_vac_soc_value]['Grid']
                p_ess=Decision[0,initial_ess_soc_value,initial_vac_soc_value]['ESS']
                p_vac=-Decision[0,initial_ess_soc_value,initial_vac_soc_value]['VAC']
                p_ev={}
                
                print("Dynamic programming calculations")
                print("PV generation:",p_pv)
                print("Import:",p_grid)
                print("ESS discharge:",p_ess)
                print("VAC charging",p_vac)
                
                
                #############################################################################
                #This section distributes virtual capacity charging power into the cars plugged chargers in the station
                
                #detect which cars are connected to the chargers in the commercial charging station
                #calculate the maximum feasible charging power input under given SoC

                dT = data_dict[None]["dT"][None]
                ESS_Max_Charge = data_dict[None]["ESS_Max_Charge_Power"][None]
                ESS_Capacity = data_dict[None]["ESS_Capacity"][None]
                

                connections=mycarpark.maxChargePowerCalculator(dT)  
                
                #Calculation of the feasible charging power at the commercial station
                feasible_ev_charging_power=min(sum(connections.values()),p_vac)
                
                for charger,maxChargePower in connections.items():    
                    power_output_of_charger=maxChargePower/feasible_ev_charging_power
                    p_ev[charger]=power_output_of_charger
                #############################################################################
                
                #############################################################################
                #This section decides what to do with the non utilized virtual capacity charging power
                
                #Power leftover: Non implemented part of virtual capacity charging power
                leftover_vac_charging_power=p_vac-feasible_ev_charging_power
                
                #Leftover is attempted to be removed with less import
                less_import=min(p_grid,leftover_vac_charging_power)
                p_grid=p_grid-less_import
            
                #Some part could be still left
                still_leftover=leftover_vac_charging_power-less_import
                    
                #Still leftover is attempted to be charged to the ESS
                
                ess_charger_limit=ESS_Max_Charge
                ess_capacity_limit=(100-initial_ess_soc_value)/100*ESS_Capacity/dT
                max_ess_charging_power=min(ess_charger_limit,ess_capacity_limit,still_leftover)               
                p_ess=p_ess-max_ess_charging_power
                
                #Final leftover: if the ESS does not allow charging all leftover, final leftover will be compensated by PV curtailment
                final_leftover=still_leftover-max_ess_charging_power
                p_pv=p_pv-final_leftover
                
                print("Implemented actions")
                print("PV generation:",p_pv)
                print("Import:",p_grid)
                print("ESS discharge:",p_ess)
                print("Real EV charging",feasible_ev_charging_power)

                stochastic_end_time = time.time()

                print("Time Information".center(80,"#"))
                print("")
                print(f"Start time: {stochastic_start_time}")
                print(f"End time: {stochastic_end_time}")
                execution_time = stochastic_end_time-stochastic_start_time
                print(f"Programming execution time: {execution_time}")
                print("")
                print("#"*80)

                time.sleep(60)

                count += 1
                if self.repetition > 0 and count >= self.repetition:
                    break

                logger.info("Optimization thread going to sleep for " + str(self.control_frequency) + " seconds")
                time_spent = self.update_count()
                for i in range(self.control_frequency - time_spent):
                    time.sleep(1)
                    if self.stopRequest.isSet():
                        break
        except Exception as e:
            logger.error("Error running instance")
            logger.error(e)
            e = str(e)
            solver_error = "The SolverFactory was unable to create the solver"
            if solver_error in e:
                i = e.index(solver_error)
                i_start = e.index("\"", i)
                i_end = e.index("\"", i_start + 1)
                solver = e[i_start + 1: i_end]
                return_msg = "Incorrect solver " + str(solver) + " used"
            else:
                return_msg = e
        finally:
            # Closing the pyomo servers
            logger.debug("Deactivating pyro servers")
            # TODO : 'SolverManager_Pyro' object has no attribute 'deactivate'
            # this error was not present before pyomo update
            # solver_manager.deactivate()
            logger.debug("Pyro servers deactivated: " + str(solver_manager))

            # If Stop signal arrives it tries to disconnect all mqtt clients
            for key, object in self.output.mqtt.items():
                object.MQTTExit()
                logger.debug("Client " + key + " is being disconnected")

            logger.info(return_msg)
            self.finish_status = True
            return return_msg
