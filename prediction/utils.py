"""
Created on Jul 09 17:38 2018

@author: nishit
"""
import logging
import subprocess

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class Utils:

    def __init__(self):
        self.container_id = "optimizationframework_ofw_1"

    def copy_files_to_host(self, container, host):
        pass
        """
        try:
            command = "cp " + container + " " + host
            logger.info("command = "+command)
            return subprocess.call(command,
                        shell=True)
        except Exception as e:
            logger.error("Error copy file to host. "+str(e))
        """

    def copy_files_from_host(self, host, container):
        pass
        """
        try:
            command = "cp " + host + " " + container
            logger.info("command = " + command)
            return subprocess.call(command,
                        shell=True)
        except Exception as e:
            logger.error("Error copy file from host. "+str(e))
        """
