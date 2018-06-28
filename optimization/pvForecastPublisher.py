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

from IO.dataPublisher import DataPublisher
from IO.radiation import Radiation

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class PVForecastPublisher(DataPublisher):

    def __init__(self, topic_params, config):
        self.pv_data = {}
        city = "Bonn, Germany"
        radiation = Radiation(city, True)
        self.q = Queue(maxsize=0)
        self.pv_thread = threading.Thread(target=self.get_pv_data_from_source, args=(radiation, self.q))
        self.pv_thread.start()

        super().__init__(topic_params, config, 30)

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

    def current_hour(self):
        date = datetime.datetime.now()
        currentHour = datetime.datetime(datetime.datetime.now().year, date.month, date.day, date.hour, 0) + \
            datetime.timedelta(hours=1)
        logger.debug(currentHour.hour)
        return int(currentHour.hour)

    def get_delay_time(self, hour, min):
        date = datetime.datetime.now()
        requestedTime = datetime.datetime(datetime.datetime.now().year, date.month, date.day, hour, min, 0)
        return requestedTime.timestamp() - time.time()

    def extract_1day_data(self):
        currenthr = self.current_hour()
        i = 0
        flag = False
        data = {}
        for row in self.pv_data:
            date = row["date"]
            hr = int(date.split(" ")[1].split(":")[0])
            if currenthr == hr:
                flag = True
            if flag and i < 24:
                data[i] = float(row["pv_output"])
                i = i + 1
            if i > 23:
                break
        return json.dumps({"P_PV_Forecast": data})

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
        data = self.extract_1day_data()
        logger.debug(str(data))
        return data
