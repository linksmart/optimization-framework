"""
Created on Jun 27 15:35 2018

@author: nishit
"""
import datetime
import json
import logging
import threading

import time
from queue import Queue

from senml import senml

from IO.dataPublisher import DataPublisher
from IO.radiation import Radiation
from IO.redisDB import RedisDB

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class PVForecastPublisher(DataPublisher):

    def __init__(self, internal_topic_params, config, id, location, maxPV, control_frequency, horizon_in_steps, dT_in_seconds):
        self.pv_data = {}
        radiation = Radiation(location, maxPV, dT_in_seconds, config)
        self.q = Queue(maxsize=0)
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.pv_thread = threading.Thread(target=self.get_pv_data_from_source, args=(radiation, self.q))
        self.pv_thread.start()
        self.topic = "P_PV"
        try:
            super().__init__(True, internal_topic_params, config, control_frequency, id)
        except Exception as e:
            redisDB = RedisDB()
            redisDB.set("Error mqtt" + self.id, True)
            logger.error(e)

    def get_pv_data_from_source(self, radiation, q):
        """PV Data fetch thread. Runs at 23:30 every day"""
        while True:
            try:
                logger.info("Fetching pv data from radiation api")
                data = radiation.get_data()
                pv_data = json.loads(data)
                q.put(pv_data)
                delay = self.get_delay_time(23, 30)
                time.sleep(delay)
            except Exception as e:
                logger.error(e)

    def get_delay_time(self, hour, min):
        date = datetime.datetime.now()
        requestedTime = datetime.datetime(date.year, date.month, date.day, hour, min, 0)
        if requestedTime < date:
            requestedTime = requestedTime + datetime.timedelta(days=1)
        return requestedTime.timestamp() - date.timestamp()

    def get_data(self):
        #  check if new data is available
        if not self.q.empty():
            try:
                new_data = self.q.get_nowait()
                self.q.task_done()
                self.pv_data = new_data
            except Exception:
                logger.debug("Queue empty")
        logger.debug("extract pv data")
        data = self.extract_horizon_data()
        return data

    def extract_horizon_data(self):
        meas = []
        if len(self.pv_data) > 0:
            current_timestamp = datetime.datetime.now()
            closest_index = self.find_closest_prev_timestamp(self.pv_data, current_timestamp)
            for i in range(self.horizon_in_steps):
                row = self.pv_data[closest_index]
                meas.append(self.get_senml_meas(float(row["pv_output"]), datetime.datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S")))
                closest_index += 1
                if closest_index >= len(self.pv_data):
                    closest_index = 0
        doc = senml.SenMLDocument(meas)
        val = doc.to_json()
        return json.dumps(val)

    def get_senml_meas(self, value, time):
        if not isinstance(time, float):
            time = float(time.timestamp())
        meas = senml.SenMLMeasurement()
        meas.time = time
        meas.value = value
        meas.name = self.topic
        return meas

    def find_closest_prev_timestamp(self, data, date):
        closest = 0
        for i, item in enumerate(data, 0):
            if datetime.datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S") <= date:
                closest = i
            else:
                break
        return closest

