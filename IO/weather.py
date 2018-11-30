import configparser
import requests
import xml.etree.ElementTree as Et
import datetime
import json

from IO.MQTTClient import MQTTClient


class WeatherData:
    def __init__(self, temp=0.0, hum=0.0, wind_dir=0.0, wind_speed=0.0, pressure=0.0, cloudy=0.0,
                 date=datetime.datetime.now()):
        self.temp = temp
        self.hum = hum
        self.wind_dir = wind_dir
        self.wind_speed = wind_speed
        self.pressure = pressure
        self.cloudy = cloudy
        self.date = date

    def default(self):
        return self.__dict__

    def __repr__(self):
        return self.date.strftime("%c")+" "+str(self.temp)+" "+str(self.hum)+" "+str(self.wind_dir)+" " + \
               str(self.wind_speed)+" "+str(self.pressure)+" "+str(self.cloudy)


class Weather:
    """
    Weatherclass for getting weather for the next few days
    """
    @staticmethod
    def get_weather(city):
        """
        Gets weather for a city
        :param city: String, name of the city
        :return:
        """

        weather_data = []
        coord = Weather.get_coordinate(city)
        weather = requests.get("https://api.met.no/weatherapi/locationforecast/1.9/?lat=" +
                               "{:.3f}".format(coord["lat"]) + "&lon=" + "{:.3f}".format(coord['lng']) + "&msl=70")
        tree = Et.fromstring(weather.content)
        for child in tree[1]:
            date = datetime.datetime.strptime(child.attrib['from'], "%Y-%m-%dT%H:%M:%SZ")
            if child.attrib['from'] == child.attrib['to'] and date <= datetime.datetime.now() + \
                    datetime.timedelta(days=1):
                weather_data.append(WeatherData(float(child[0][0].attrib["value"]), float(child[0][3].attrib["value"]),
                                                float(child[0][1].attrib["deg"]), float(child[0][2].attrib["mps"]),
                                                float(child[0][4].attrib["value"]),
                                                float(child[0][5].attrib["percent"]),
                                                date))
        Weather.expand_data(weather_data)
        weather_data = sorted(weather_data, key=lambda w: w.date)
        return weather_data

    @staticmethod
    def expand_data(weather):
        for i in range(0, len(weather)-1):
            startdate = weather[i].date
            for j in range(1, 60):
                date = startdate + datetime.timedelta(minutes=j)
                wd = WeatherData()
                wd.date = date
                for col in ["temp", "hum", "wind_dir", "wind_speed", "pressure", "cloudy"]:
                    start = float(getattr(weather[i], col))
                    end = float(getattr(weather[i+1], col))
                    step = (end - start) / 60
                    setattr(wd, col, start + step * j)
                weather.append(wd)

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


we = Weather.get_weather("Bonn, Germany")
js = json.dumps([wea.__dict__ for wea in we], default=str)

m = MQTTClient("optiframework_mosquitto_1", 1883, "weatherClient")
m.publish("data/weather", str(js), True)
m.MQTTExit()
