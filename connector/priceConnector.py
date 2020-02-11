"""
Created on Mär 27 12:18 2019

@author: nishit
"""
import datetime

from connector.apiConnector import ApiConnector

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent(parent="connector")

class PriceConnector(ApiConnector):

    def __init__(self, url, config, house):
        self.num_of_days = 1
        super().__init__(url, config, house, "price")

    def update_url(self):
        today = datetime.datetime.now()
        start_date = today.strftime("%Y-%m-%d")
        today = today + datetime.timedelta(days=self.num_of_days)
        end_date = today.strftime("%Y-%m-%d")

        pos = self.url.find("/prices")
        base_url = self.url[0:pos + 7]
        self.url = base_url + "/" + start_date + "/" + end_date

    def extract_data(self, raw_data):
        time_series = raw_data["Publication_MarketDocument"]["TimeSeries"]
        data = []
        if isinstance(time_series, list):
            for time_frame in time_series:
                data = self.extract_time_series(data, time_frame)
        elif isinstance(time_series, dict):
            data = self.extract_time_series(data, time_series)
        if len(data) < self.num_of_days * 24:
            logger.error("Less than " + str(self.num_of_days * 24) + " hrs of price data")
            logger.debug("raw price data = "+str(raw_data))
        logger.debug("raw price data = " + str(raw_data))
        data = self.duplicate_data(data)
        return data

    def extract_time_series(self, data, time_frame):
        unit = time_frame["price_Measure_Unit.name"]
        start_time = time_frame["Period"]["timeInterval"]["start"]
        start_time = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%MZ")
        start_time = start_time.timestamp()
        for point in time_frame["Period"]["Point"]:
            position = int(point["position"]) - 1
            price = float(point["price.amount"])
            t = start_time + (position - 1) * 3600
            data.append([t, price, unit])
        return data

    def duplicate_data(self, data):
        time_diff = len(data) * 3600
        new_data = []
        for t, price, unit in data:
            new_data.append([t+time_diff, price, unit])
        data.extend(new_data)
        return data
