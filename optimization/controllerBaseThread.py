"""
Created on Apr 24 16:10 2019

@author: nishit
"""
import threading
from abc import ABC


import pyutilib.subprocess.GlobalData

from optimization.controllerBase import ControllerBase

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False


class ControllerBaseThread(ControllerBase, threading.Thread, ABC):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds, optimization_type):
        super(ControllerBaseThread, self).__init__(id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                         config, horizon_in_steps, dT_in_seconds, optimization_type)

    def join(self, timeout=None):
        # self.stopRequest.set()
        super(ControllerBaseThread, self).join(timeout)

    def Stop(self):
        self.exit()
        if self.isAlive():
            self.join(1)

    # Start the optimization process and gives back a result
    def run(self):
        self.run_method()
