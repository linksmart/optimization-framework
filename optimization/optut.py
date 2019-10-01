"""
Created on Okt 01 16:11 2019

@author: nishit
"""

from pyomo.environ import *
from pyomo.opt import SolverStatus, TerminationCondition


import pyutilib.subprocess.GlobalData


pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False


class OptUt:

    def thread_solver(self, single_ev, data_dict, ini_ess_soc, ini_vac_soc, solver_name, timestep, absolute_path):
        v = str(timestep)+"_"+str(ini_ess_soc)+"_"+str(ini_vac_soc)
        result = None
        instance = None
        while True:
            try:
                #if True:#redisDB.get_lock("opt_lock", v):
                optsolver = SolverFactory(solver_name)
                spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
                module = spec.loader.load_module(spec.name)
                my_class = getattr(module, 'Model')
                instance = my_class.model.create_instance(data_dict)
                result = optsolver.solve(instance)
                #self.logger.debug("result "+str(result))
            except Exception as e:
                print("Thread: "+v+ " "+str(e))
            finally:
                pass
                #redisDB.release_lock("opt_lock", v)

            #ini_ess_soc = instance_object["ess_soc"]  # instance_info[instance].ini_ess_soc
            #ini_vac_soc = instance_object["vac_soc"]  # instance_info[instance].ini_vac_soc
            if single_ev:
                position = False#instance_object["position"]  # instance_info[instance].position
            # self.logger.debug("solver status "+str(result.solver.status))
            # self.logger.debug("termination condition " + str(result.solver.termination_condition))
            if result is None:
                print("result is none for "+str(v)+ " repeat")
            elif (result.solver.status == SolverStatus.ok) and (
                    result.solver.termination_condition == TerminationCondition.optimal):

                instance.solutions.load_from(result)

                # * if solved get the values in dict

                my_dict = {}
                for v in instance.component_objects(Var, active=True):
                    # self.logger.debug("Variable in the optimization: " + str(v))
                    varobject = getattr(instance, str(v))
                    var_list = []
                    try:
                        # Try and add to the dictionary by key ref
                        for index in varobject:
                            var_list.append(varobject[index].value)
                        # self.logger.debug("Identified variables " + str(var_list))
                        my_dict[str(v)] = var_list
                    except Exception as e:
                        print("error reading result " + str(e))

                if single_ev:
                    combined_key = (timestep, ini_ess_soc, ini_vac_soc, position)
                else:
                    combined_key = (timestep, ini_ess_soc, ini_vac_soc)

                Decision = {combined_key:{}}
                Decision[combined_key]['Grid'] = my_dict["P_GRID_OUTPUT"][0]
                Decision[combined_key]['PV'] = my_dict["P_PV_OUTPUT"][0]
                Decision[combined_key]['ESS'] = my_dict["P_ESS_OUTPUT"][0]
                Decision[combined_key]['VAC'] = my_dict["P_VAC_OUTPUT"][0]

                Value = {combined_key:{}}
                Value[combined_key] = my_dict["P_PV_OUTPUT"][0]
                #self.logger.debug("Value "+str(Value))
                return (Decision, Value)

            elif result.solver.termination_condition == TerminationCondition.infeasible:
                # do something about it? or exit?
                print("Termination condition is infeasible "+v + " repeat")
            else:
                print("Nothing fits "+v + " repeat")
