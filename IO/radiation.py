import configparser
import datetime
import json
from math import floor, ceil

import requests

from IO.locationData import LocationData

from utils_intern.messageLogger import MessageLogger
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
    def __init__(self, date=datetime.datetime.now(), pv_output=0.0, beam_irradiance=0.0,
                 diffuse_irradiance=0.0, reflected_irradiance=0.0, sun_elevation=0.0, air_temp=0.0,
                 wind_speed=0.0):
        self.date = datetime.datetime(datetime.datetime.now().year, date.month, date.day, date.hour, 0) + \
                    datetime.timedelta(hours=1)
        self.pv_output = pv_output
        self.beam_irradiance = beam_irradiance
        self.diffuse_irradiance = diffuse_irradiance
        self.reflected_irradiance = reflected_irradiance
        self.sun_elevation = sun_elevation
        self.air_temp = air_temp
        self.wind_speed = wind_speed

    def default(self):
        return self.__dict__

    def __repr__(self):
        return self.date.strftime("%c") + " " + str(self.pv_output) + " " + str(self.beam_irradiance) + " " + \
               str(self.diffuse_irradiance) + " " + str(self.reflected_irradiance) + " " + str(self.sun_elevation) + \
               " " + str(self.air_temp) + " " + str(self.wind_speed)


class SolarRadiation:
    """
    Radiation Service that collects data and grep the next 48h
    """
    @staticmethod
    def get_rad(lat, lon, maxPV, dT):
        rad_data = []
        logger.info("coord "+str(lat)+ ", "+ str(lon))
        if lat is not None and lon is not None:
            rad = requests.get("http://re.jrc.ec.europa.eu/pvgis5/seriescalc.php?lat=" +
                               "{:.3f}".format(float(lat)) + "&lon=" + "{:.3f}".format(float(lon)) + "&raddatabase=" +
                               "PVGIS-CMSAF&usehorizon=1&startyear=2016&endyear=2016&mountingplace=free&" +
                               "optimalinclination=0&optimalangles=1&hourlyoptimalangles=1&PVcalculation=1&" +
                               "pvtechchoice=crystSi&peakpower=" + str(maxPV) + "&loss=14&components=1")
            red_arr = str(rad.content).split("\\n")
            for x in range(11):
                del red_arr[0]
            now_file = datetime.datetime.now()
            now = datetime.datetime(2000, now_file.month, now_file.day, now_file.hour, now_file.minute)
            for x in range(0, red_arr.__len__()):
                w = red_arr[x][:-2].split(",")
                if w.__len__() != 9:
                    break
                date_file = datetime.datetime.strptime(w[0], "%Y%m%d:%H%M%S")
                date = datetime.datetime(2000, date_file.month, date_file.day, date_file.hour, date_file.minute)
                if now <= date - datetime.timedelta(hours=-1) <= (now + datetime.timedelta(hours=48)):
                    rad_data.append(RadiationData(date, w[1], w[2], w[3], w[4], w[5], w[6], w[7]))
            we = sorted(rad_data, key=lambda w: w.date)
            data = SolarRadiation.extract_data(we)
            data = SolarRadiation.expand_and_resample(data, dT)
            return data

    @staticmethod
    def extract_data(rad):
        data = []
        for i in range(0, len(rad) - 1):
            date = rad[i].date
            timestamp = date.timestamp()
            pv_output = float(rad[i].pv_output)
            data.append([timestamp, pv_output])
        return data

    @staticmethod
    def expand_and_resample(raw_data, dT):
        step = float(dT)
        j = len(raw_data) - 1
        new_data = []
        if j > 0:
            start_time = raw_data[j][0]
            start_value = raw_data[j][1]
            new_data.append([start_time, start_value])
            prev_time = start_time
            prev_value = start_value
            required_diff = step
            j -= 1
            while j >= 0:
                end_time = raw_data[j][0]
                end_value = raw_data[j][1]
                diff_sec = prev_time - end_time
                if diff_sec >= required_diff:
                    ratio = required_diff / diff_sec
                    inter_time = prev_time - required_diff
                    inter_value = prev_value - (prev_value - end_value) * ratio
                    new_data.append([inter_time, inter_value])
                    prev_time = inter_time
                    prev_value = inter_value
                    required_diff = step
                else:
                    required_diff -= diff_sec
                    prev_time = end_time
                    prev_value = end_value
                    j -= 1
        else:
            new_data = raw_data
        new_data.reverse()
        return new_data


class Radiation:

    def __init__(self, config, maxPV, dT_in_seconds, location):
        self.data = {}
        self.location = location
        self.location_data = LocationData(config)
        self.location_found = False
        self.lat = 50.7374
        self.lon = 7.0982
        self.maxPV = maxPV
        #self.maxPV /= 1000  # pv in kW
        self.dT_in_seconds = dT_in_seconds

    def get_data(self):
        self.update_location_info()
        data = SolarRadiation.get_rad(self.lat, self.lon, self.maxPV, self.dT_in_seconds)
        jsm = json.dumps(data, default=str)
        return jsm

    def update_location_info(self):
        if not self.location_found:
            lat, lon = self.location_data.get_city_coordinate(self.location["city"], self.location["country"])
            if lat is not None and lon is not None:
                self.lat = lat
                self.lon = lon
                self.location_found = True
            else:
                logger.error("Error getting location info, setting to bonn, germany")