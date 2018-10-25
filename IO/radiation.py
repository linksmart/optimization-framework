import configparser
import datetime
import json
import logging

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
    def get_rad(city, maxPV):
        rad_data = []
        coord = SolarRadiation.get_coordinate(city)
        logger.info("coord "+str(coord))
        rad = requests.get("http://re.jrc.ec.europa.eu/pvgis5/seriescalc.php?lat=" +
                           "{:.3f}".format(coord["lat"]) + "&lon=" + "{:.3f}".format(coord['lng']) + "&raddatabase=" +
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
            date_file = datetime.datetime.strptime(w[0], "%Y%m%d:%H%M")
            date = datetime.datetime(2000, date_file.month, date_file.day, date_file.hour, date_file.minute)
            if now <= date - datetime.timedelta(hours=-1) <= (now + datetime.timedelta(hours=48)):
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
    def get_coordinate(city):
        """
        Get geocoordinate from City name
        :param city:
        :return: Union[Type[JSONDecoder], Any]
        """
        try:
            config = configparser.RawConfigParser()
            config.read("utils/ConfigFile.properties")
            googlekey = config.get("SolverSection", "googleapikey")
            request = requests.get("https://maps.googleapis.com/maps/api/geocode/json?address=" + city + "&key=" +
                                   googlekey)
            text = request.json()
            return text["results"][0]["geometry"]["location"]
        except KeyError:
            return ""


class Radiation:

    def __init__(self, city, hours, maxPV):
        self.data = {}
        self.city = city
        self.hours = hours
        self.maxPV = maxPV
        self.maxPV /= 1000  # pv in kW

    def get_data(self):
        we = SolarRadiation.get_rad(self.city, self.maxPV)
        if self.hours:
            jsh = json.dumps([wea.__dict__ for wea in we], default=str)
            return jsh
        else:
            SolarRadiation.expand_data(we)
            we = sorted(we, key=lambda w: w.date)
            jsm = json.dumps([wea.__dict__ for wea in we], default=str)
            return jsm