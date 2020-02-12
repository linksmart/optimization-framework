"""
Created on Jan 28 16:28 2020

@author: nishit
"""

import configparser
from config.configUpdater import ConfigUpdater
from monitor.instanceMonitor import InstanceMonitor
import signal
import sys

from utils_intern.messageLogger import MessageLogger

def sigterm(x, y):
    print('SIGTERM received, time to leave.')
    if monitor:
        monitor.Stop()

# Register the signal to the handler
signal.signal(signal.SIGTERM, sigterm)  # Used by this script

monitor = None

if __name__ == '__main__':
    config_path = "/usr/src/app/monitor/resources/monitorConfig.properties"
    config_path_default = "/usr/src/app/config/monitorConfig.properties"
    config, logger = ConfigUpdater.get_config_and_logger("monitor", config_path_default, config_path)

    monitor = InstanceMonitor(config)

    print("Monitor started")
