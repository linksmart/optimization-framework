"""
Created on Jun 27 15:34 2018

@author: nishit
"""
import datetime
import json
import logging

import os

from IO.dataPublisher import DataPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class LoadForecastPublisher(DataPublisher):

    def __init__(self, internal_topic_params, config, queue, publish_frequency, topic, id, horizon_in_steps, dT_in_seconds):
        self.load_data = {}
        self.flag = True
        self.file_path = os.path.join("/usr/src/app", "optimization", "loadData.dat")
        self.q = queue
        self.topic = topic
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        super().__init__(True, internal_topic_params, config, publish_frequency, id)

    def get_data(self):
        try:
            #  check if new data is available
            if not self.q.empty():
                try:
                    new_data = self.q.get_nowait()
                    self.q.task_done()
                    self.load_data = new_data
                except Exception:
                    logger.debug("Queue empty")
            if not self.load_data:
                return None
            logger.debug("extract load data")
            data = self.extract_horizon_data()
            logger.debug(str(data))
            return data
        except Exception as e:
            logger.error(str(e))
            return None

    def extract_horizon_data(self):
        data = {}
        list = self.load_data.items()
        list = sorted(list)
        list = list[-self.horizon_in_steps:]
        for i in range(self.horizon_in_steps):
            if list[i][1] < 0:
                data[i] = list[i][1]
            else:
                data[i] = -0.000001
        return json.dumps({self.topic: data})

