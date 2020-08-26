import datetime

from influxdb import InfluxDBClient

from IO.influxDBmanager import InfluxDBManager
from utils_intern.constants import Constants

d = datetime.datetime.now()

if isinstance(d, datetime.datetime):
    print("yes")
else:
    print("no")

exit(0)

Constants.influx_host = "localhost"
Constants.influx_retention = "4d"
#idb = InfluxDBManager()

json_body = [
    {
        "measurement": "cpu_load_short",
        "tags": {
            "host": "server01",
            "region": "us-west"
        },
        "time": "2020-08-23T23:00:00Z",
        "fields": {
            "value": 0.64
        }
    },
{
        "measurement": "cpu_load_short",
        "tags": {
            "host": "server02",
            "region": "us-west"
        },
        "time": "2020-08-23T23:00:00Z",
        "fields": {
            "value": 0.63
        }
    }
]

client = InfluxDBClient('localhost', 8086, 'root', 'root', 'example')

client.create_database('example')

client.write_points(json_body)

result = client.query("select value from cpu_load_short where host='server02';")

print("Result: {0}".format(result))


"select rmse from P_Load;"