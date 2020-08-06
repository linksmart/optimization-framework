import configparser
import datetime
import json
from math import floor, ceil

import os
import requests

from IO.locationData import LocationData

from utils_intern.messageLogger import MessageLogger
from utils_intern.timeSeries import TimeSeries

logger = MessageLogger.get_logger_parent()


# Date  = Date & time (UTC)
# EPV   = PV power output if requested (W)
# Bi    = In-plane beam irradiance (W/m2)
# Di    = Diffuse in-plane irradiance (W/m2) (if radiation components are requested)
# Ri    = Refleted in-plane irradiance (W/m2) (if radiation components are requested)
# As    = Sun elevation (degrees above horizon)
# Tamb  = Air temperature (°C)
# W10   = Wind speed at 10m (m/s)

class RadiationData:
    def __init__(self, date, pv_output):
        self.date = datetime.datetime(date.year, date.month, date.day, date.hour, 0)
        self.pv_output = pv_output

    def default(self):
        return self.__dict__

    def __repr__(self):
        return self.date.strftime("%c") + " " + str(self.pv_output)


class Radiation:

    def __init__(self, config, maxPV, dT_in_seconds, location, horizon_in_steps):
        self.base_data = []
        self.city = location["city"]
        self.country = location["country"]
        self.location_data = LocationData(config)
        self.location_found = False
        self.lat = 50.7374
        self.lon = 7.0982
        self.maxPV = maxPV  # pv in kW
        self.dT_in_seconds = dT_in_seconds
        self.horizon_hours = int((dT_in_seconds * horizon_in_steps)/3600) + 2
        self.start_date = datetime.datetime.now().replace(year=2016, month=1, day=1, hour=1, minute=0, second=0, microsecond=0)
        pv_data_base_path = config.get("IO", "pv.data.base.path")
        self.pv_data_path = os.path.join("/usr/src/app/", pv_data_base_path,
                                         "pv_data_" + str(self.city.casefold()) + "_" + str(
                                             self.country.casefold()) + ".txt")
        self.fetch_base_data()

    # values from api are sampled at 55 min mark every hour,
    # and we assume it to be for next hr (5min shift)
    def fetch_base_data(self):
        pv_data = self.read_data_from_file()
        if pv_data is None:
            self.update_location_info()
            data = self.get_rad_for_year()
            pv_data = self.extract_pv_data(data)
            self.save_data_to_file(pv_data)
        else:
            logger.debug("pv data found in file " + str(self.pv_data_path))
        self.base_data = self.adjust_data_for_max_PV(pv_data)
        if len(self.base_data) > 0:
            logger.info("PV base data loaded")

    # values from api are sampled at 55 min mark every hour,
    # and we assume it to be for next hr (5min shift)
    def get_data(self, timestamp):
        if len(self.base_data) == 0:
            self.fetch_base_data()
        if len(self.base_data) > 0:
            data, start_time = self.filter_next_horizon_hrs(timestamp)
            data = self.append_timestamp(data, start_time)
            data = TimeSeries.expand_and_resample(data, self.dT_in_seconds, False)
            return data

    # values from api are sampled at 55 min mark every hour,
    # and we assume it to be for next hr (5min shift)
    def get_complete_data(self):
        if len(self.base_data) == 0:
            self.fetch_base_data()
        if len(self.base_data) > 0:
            data = self.append_timestamp(self.base_data.copy(), self.start_date.timestamp())
            return data

    def update_location_info(self):
        if not self.location_found:
            lat, lon = self.location_data.get_city_coordinate(self.city, self.country)
            if lat is not None and lon is not None:
                self.lat = lat
                self.lon = lon
                self.location_found = True
            else:
                logger.error("Error getting location info, setting to bonn, germany")

    def get_rad_for_year(self):
        logger.debug("Querying pv data from api")
        rad_data = []
        logger.info("coord " + str(self.lat) + ", " + str(self.lon))
        if self.lat is not None and self.lon is not None:
            rad = requests.get("http://re.jrc.ec.europa.eu/pvgis5/seriescalc.php?lat=" +
                               "{:.3f}".format(float(self.lat)) + "&lon=" + "{:.3f}".format(
                float(self.lon)) + "&raddatabase=" +
                               "PVGIS-CMSAF&usehorizon=1&startyear=2016&endyear=2016&mountingplace=free&" +
                               "optimalinclination=0&optimalangles=1&hourlyoptimalangles=1&PVcalculation=1&" +
                               "pvtechchoice=crystSi&peakpower=1&loss=14&components=1")
            red_arr = str(rad.content).split("\\n")
            for x in range(11):
                del red_arr[0]
            for x in range(0, red_arr.__len__()):
                w = red_arr[x][:-2].split(",")
                if w.__len__() != 9:
                    break
                date_file = datetime.datetime.strptime(w[0], "%Y%m%d:%H%M%S")
                date = datetime.datetime(2016, date_file.month, date_file.day, date_file.hour, date_file.minute)
                rad_data.append(RadiationData(date, w[1]))
            we = sorted(rad_data, key=lambda w: w.date)
            return we
        return rad_data

    def extract_pv_data(self, data):
        pv_data = []
        for i in range(len(data)):
            pv_output = float(data[i].pv_output)
            pv_data.append(pv_output)
        return pv_data

    def save_data_to_file(self, pv_data):
        if len(pv_data) > 0:
            try:
                with open(self.pv_data_path, "w+") as f:
                    pv_data = [str(i) + "\n" for i in pv_data]
                    f.writelines(pv_data)
            except Exception as e:
                logger.error("Error saving pv data to file " + str(self.pv_data_path) + " , " + str(e))

    def read_data_from_file(self):
        try:
            if os.path.exists(self.pv_data_path):
                with open(self.pv_data_path, "r") as f:
                    data = f.readlines()
                    return data
            else:
                logger.debug("pv data file not found " + self.pv_data_path)
        except Exception as e:
            logger.error("Error reading pv data to file " + str(self.pv_data_path) + " , " + str(e))
        return None

    def adjust_data_for_max_PV(self, data):
        return [float(i) * self.maxPV for i in data]

    # values from api are sampled at 55 min mark every hour,
    # and we assume it to be for next hr (5min shift)
    def get_row_by_time(self, timestamp):
        now = datetime.datetime.fromtimestamp(timestamp)
        end_date = now.replace(year=2016, minute=0, second=0, microsecond=0)
        present_date = now.replace(minute=0, second=0, microsecond=0)
        total_seconds = (end_date - self.start_date).total_seconds()
        total_hrs = int(total_seconds / 3600)
        return (total_hrs, present_date.timestamp())

    def filter_next_horizon_hrs(self, timestamp):
        index, timestamp = self.get_row_by_time(timestamp)
        index = index % len(self.base_data)
        range = self.horizon_hours
        carry = range - (len(self.base_data) - index)
        if carry < 0:
            carry = 0
        filtered_data = self.base_data[index:index + range] + self.base_data[:carry]
        return (filtered_data, timestamp)

    def append_timestamp(self, data, timestamp):
        new_data = []
        for row in data:
            new_data.append([timestamp, row])
            timestamp += 3600
        return new_data