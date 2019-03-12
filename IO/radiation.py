import configparser
import datetime
import json
import logging
from math import floor, ceil

import requests

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

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
    def get_rad(lat, lon, maxPV):
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
                if now <= date - datetime.timedelta(hours=-2) <= (now + datetime.timedelta(hours=47)):
                    rad_data.append(RadiationData(date, w[1], w[2], w[3], w[4], w[5], w[6], w[7]))
            return rad_data

    @staticmethod
    def expand_data(rad):
        for i in range(0, len(rad) - 1):
            startdate = rad[i].date
            for j in range(1, 60):
                date = startdate + datetime.timedelta(minutes=j)
                wd = RadiationData()
                wd.date = date
                for col in ["pv_output", "beam_irradiance", "diffuse_irradiance", "reflected_irradiance",
                            "sun_elevation", "air_temp", "wind_speed"]:
                    start = float(getattr(rad[i], col))
                    end = float(getattr(rad[i + 1], col))
                    step = (end - start) / 60
                    setattr(wd, col, start + step * j)
                rad.append(wd)

    @staticmethod
    def expand_data_hr_to_sec(rad, step):
        j = 0.0
        new_rad = []
        while j < len(rad) - 1:
            if j.is_integer():
                i = int(j)
                new_rad.append(rad[i])
            else:
                i = floor(j)
                ratio = j - i
                startdate = rad[i].date
                sec = int(3600.0 * ratio)
                date = startdate + datetime.timedelta(seconds=sec)
                wd = RadiationData()
                wd.date = date
                for col in ["pv_output", "beam_irradiance", "diffuse_irradiance", "reflected_irradiance",
                            "sun_elevation", "air_temp", "wind_speed"]:
                    start = float(getattr(rad[i], col))
                    end = float(getattr(rad[i+1], col))
                    val = start + (end - start) * ratio
                    setattr(wd, col, val)
                new_rad.append(wd)
            j += step
        return new_rad

class Radiation:

    def __init__(self, lat, lon, maxPV, dT_in_seconds):
        self.data = {}
        self.lat = lat
        self.lon = lon
        self.maxPV = maxPV
        self.maxPV /= 1000  # pv in kW
        self.dT_in_seconds = dT_in_seconds
        self.hours = False
        if self.dT_in_seconds == 3600:
            self.hours = True
        self.step = float(self.dT_in_seconds/3600.0)

    def get_data(self):
        we = SolarRadiation.get_rad(self.lat, self.lon, self.maxPV)
        if self.hours:
            we = sorted(we, key=lambda w: w.date)
            jsh = json.dumps([wea.__dict__ for wea in we], default=str)
            return jsh
        else:
            we = SolarRadiation.expand_data_hr_to_sec(we, self.step)
            we = sorted(we, key=lambda w: w.date)
            jsm = json.dumps([wea.__dict__ for wea in we], default=str)
            return jsm