"""
Created on Jun 27 15:35 2018

@author: nishit
"""
import datetime
import json

from senml import senml

from IO.dataPublisher import DataPublisher
from IO.redisDB import RedisDB
from utils_intern.messageLogger import MessageLogger


class PVForecastPublisher(DataPublisher):

    def __init__(self, internal_topic_params, config, id, control_frequency, horizon_in_steps, dT_in_seconds, q):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.pv_data = {}
        self.q = q
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.topic = "P_PV"
        try:
            super().__init__(True, internal_topic_params, config, control_frequency, id)
        except Exception as e:
            redisDB = RedisDB()
            redisDB.set("Error mqtt" + self.id, True)
            self.logger.error(e)

    def get_data(self):
        #  check if new data is available
        if not self.q.empty():
            try:
                new_data = self.q.get_nowait()
                self.q.task_done()
                self.pv_data = new_data
                self.logger.debug("extract pv data")
                data = self.extract_horizon_data()
                return data
            except Exception:
                self.logger.debug("Queue empty")
        return None

    def extract_horizon_data(self):
        meas = []
        if len(self.pv_data) > 0:
            current_timestamp = datetime.datetime.now().timestamp()
            closest_index = self.find_closest_prev_timestamp(self.pv_data, current_timestamp)
            for i in range(self.horizon_in_steps):
                row = self.pv_data[closest_index]
                meas.append(self.get_senml_meas(float(row[1]), row[0]))
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
            if item[0] <= date:
                closest = i
            else:
                break
        return closest

