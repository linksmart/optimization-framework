"""
Created on Mär 27 12:18 2019

@author: nishit
"""
import datetime

from connector.apiConnector import ApiConnector

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class PriceConnector(ApiConnector):

    def __init__(self, url, config, house):
        super().__init__(url, config, house, "price")

    def update_url(self):
        today = datetime.datetime.now()
        start_date = today.strftime("%Y-%m-%d")
        today = today + datetime.timedelta(days=2)
        end_date = today.strftime("%Y-%m-%d")

        pos = self.url.find("/prices")
        base_url = self.url[0:pos + 7]
        self.url = base_url + "/" + start_date + "/" + end_date

    def extract_data(self, raw_data):
        time_series = raw_data["Publication_MarketDocument"]["TimeSeries"]
        data = []
        if isinstance(time_series, list):
            for time_frame in time_series:
                self.extract_time_series(data, time_frame)
        elif isinstance(time_series, dict):
            self.extract_time_series(data, time_series)
        if len(data) < 48:
            logger.error("Less than 48 hrs of price data")
            logger.debug("raw price data = "+str(raw_data))
        logger.debug("raw price data = " + str(raw_data))
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