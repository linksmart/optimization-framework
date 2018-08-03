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

    def __init__(self, internal_topic_params, config, queue, publish_frequency):
        self.load_data = {}
        self.flag = True
        self.file_path = os.path.join("/usr/src/app", "optimization", "loadData.dat")
        self.q = queue
        super().__init__(internal_topic_params, config, publish_frequency)

    def get_data(self):
        #  check if new data is available
        if not self.q.empty():
            try:
                new_data = self.q.get_nowait()
                self.q.task_done()
                self.load_data = new_data
            except Exception:
                logger.debug("Queue empty")
        logger.debug("extract load data")
        if not self.load_data:
            return None
        data = self.extract_1day_data()
        logger.debug(str(data))
        return data

    def current_datetime(self, delta):
        date = datetime.datetime.now()
        currentHour = datetime.datetime(datetime.datetime.now().year, 12, 11, 5, 0) + \
            datetime.timedelta(hours=delta)
        return currentHour

    def extract_1day_data(self):
        delta = 1
        data = {}
        while delta <= 24:
            date = self.current_datetime(delta)
            data[int(delta-1)] = self.load_data[date]
            delta += 1
        logger.info("load d = "+str(data))
        return json.dumps({"P_Load_Forecast": data})

    def test_data(self):
        data = {}
        data[0] = 0.10
        data[1] = 0.11
        data[2] = 0.12
        return json.dumps({"P_Load_Forecast": data})
