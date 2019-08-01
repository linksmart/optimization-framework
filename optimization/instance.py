"""
Created on Apr 26 16:29 2019

@author: nishit
"""


class Instance:

    def __init__(self, instance_id, ini_ess_soc, ini_vac_soc, position = None, instance=None):
        self.instance_id = instance_id
        self.ini_ess_soc = ini_ess_soc
        self.ini_vac_soc = ini_vac_soc
        self.position = position
        self.instance = instance

    def addResult(self, result):
        self.result = result
