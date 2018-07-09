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

    def copy_files_to_host(self, source, target):
        try:
            return subprocess.call("docker cp " + self.container_id + ":" + source + " " + target,
                        shell=True,
                        stdout=subprocess.STDOUT,
                        stderr=subprocess.STDOUT)
        except Exception as e:
            logger.error("Error copy file to host. "+str(e))

    def copy_files_from_host(self, source, target):
        try:
            return subprocess.call("docker cp " + target + " " + self.container_id + ":" + source + " ",
                        shell=True,
                        stdout=subprocess.STDOUT,
                        stderr=subprocess.STDOUT)
        except Exception as e:
            logger.error("Error copy file from host. "+str(e))
