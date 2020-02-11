"""
Created on Feb 11 10:32 2020

@author: nishit
"""
import threading
import time

from IO.monitorPub import MonitorPub
from utils_intern.messageLogger import MessageLogger

logger = MessageLogger.get_logger_parent(parent="connector")

class MonitorConnectors:

    def __init__(self, config):
        self.status = {}
        self.ping_frequency = config.getint("IO", "ping.frequency")
        self.monitor = MonitorPub(config, id="connector")
        self.check_ping_thread = threading.Thread(target=self.check_pings)
        self.check_ping_thread.start()
        logger.info("initialized monitor connector")

    def ping(self, name):
        self.status[name] = int(time.time())
        logger.info("ping by "+str(name))

    def check_pings(self):
        while True:
            logger.debug("ping status : "+str(self.status))
            current_time = int(time.time())
            ping_delayed = False
            for name, last in self.status.items():
                if current_time - last > self.ping_frequency:
                    ping_delayed = True
                    break

            if not ping_delayed:
                self.monitor.send_monitor_ping(self.ping_frequency)
                logger.info("monitor ping sent")
            else:
                logger.info("monitor ping not sent")

            sleep_time = self.ping_frequency - (time.time() - current_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
