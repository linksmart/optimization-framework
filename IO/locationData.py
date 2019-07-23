"""
Created on Mär 11 15:12 2019

@author: nishit
"""
import os
import requests


from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class LocationData:

    def __init__(self, config):
        # city, county, lat, lon
        path = config.get("IO", "location.data.path")
        self.dir_path = os.path.join("/usr/src/app/", path)
        self.file_path = os.path.join(self.dir_path, "location_data.csv")
        self.provider = config.get("IO", "location.api.provider") #osm, google
        if self.provider == "google":
            self.googleApiKey = config.get("SolverSection", "googleapikey")

    def get_city_coordinate(self, city, country):
        lat, lon = self.find_city(city, country)
        if (lat is None or lon is None) and self.provider is not None:
            if self.provider == "osm":
                lat, lon = self.get_coordinate_osm(city, country)
            elif self.provider == "google":
                lat, lon = self.get_coordinate_google(city, country)
            if lat is not None and lon is not None:
                self.save_city(city, country, lat, lon)
        return lat, lon

    def find_city(self, city, country):
        lat = None
        lon = None
        if self.file_path and os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                lines = file.readlines()
                for line in lines:
                    if city in line and country in line:
                        row = line.split(",")
                        if len(row) == 4:
                            c = row[0].strip()
                            con = row[1].strip()
                            if c == city and con == country:
                                lat = float(row[2].strip())
                                lon = float(row[3].strip())
                                break
        return lat, lon

    def save_city(self, city, country, lat, lon):
        if city is not None and len(city) > 0 and \
                country is not None and len(country) > 0 and \
                lat is not None and lon is not None:
            if self.file_path:
                if not os.path.exists(self.dir_path):
                    os.makedirs(self.dir_path)
                logger.info("location file "+ self.file_path)
                with open(self.file_path, "a+") as file:
                    line = city + "," + country + "," + str(lat) + "," + str(lon) + "\n"
                    file.write(line)

    def get_coordinate_google(self, city, country):
        """
        Get geocoordinate from City name
        :param city:
        :return: Union[Type[JSONDecoder], Any]
        """
        try:
            location = city + ", " + country
            request = requests.get("https://maps.googleapis.com/maps/api/geocode/json?address=" + location + "&key=" +
                                   self.googleApiKey)
            text = request.json()
            logger.info(text)
            if len(text) > 0:
                coord = text["results"][0]["geometry"]["location"]
                return float(coord["lat"]), float(coord['lng'])
        except KeyError:
            pass
        return None, None

    def get_coordinate_osm(self, city, country):
        try:
            request = requests.get("https://nominatim.openstreetmap.org/search?city=" + city + "&country="
                                   + country + "&format=json")
            text = request.json()
            logger.info(text)
            if len(text) > 0:
                coord = text[0]
                return float(coord["lat"]), float(coord['lon'])
            else:
                return self.get_coordinate_osm_q(city, country)
        except Exception:
            pass
        return None, None

    def get_coordinate_osm_q(self, city, country):
        try:
            location = city + "," + country
            request = requests.get("https://nominatim.openstreetmap.org/search?q=" + location + "&format=json")
            text = request.json()
            logger.info(text)
            if len(text) > 0:
                coord = text[0]
                return float(coord["lat"]), float(coord['lon'])
        except Exception:
            pass
        return None, None