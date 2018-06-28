"""
Created on Jun 27 15:34 2018

@author: nishit
"""
import json

import os

from IO.dataPublisher import DataPublisher


class LoadForecastPublisher(DataPublisher):

    def __init__(self, topic_params, config):
        self.load_data = {}
        self.flag = True
        self.file_path = os.path.join("/usr/src/app", "optimization", "loadData.dat")
        super().__init__(topic_params, config, 30)

    def get_data(self):
        if self.flag:
            data = {}
            with open(self.file_path) as f:
                for line in f:
                    time, load = line.split()
                    time = int(time)
                    load = float(load)
                    data[time] = load
            self.load_data["P_Load_Forecast"] = data
            print(self.load_data)
        return json.dumps(self.load_data)
