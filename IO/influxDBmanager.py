import datetime

from influxdb import InfluxDBClient

from utils_intern.constants import Constants
from utils_intern.messageLogger import MessageLogger

logger = MessageLogger.get_logger_parent()


class InfluxDBManager:

    def __init__(self):
        self.influx_db = InfluxDBClient(Constants.influx_host, 8086, database='S4G')
        self.influx_db.create_database('S4G')
        try:
            self.influx_db.create_retention_policy("raw_data_retention", Constants.influx_retention, replication="1", database="S4G", default=True)
        except Exception as e:
            if "retention policy already exists" in str(e):
                self.influx_db.alter_retention_policy("raw_data_retention", duration=Constants.influx_retention,
                                                       database="S4G", default=True)

    def write(self, json_body):
        try:
            if json_body is not None:
                r = self.influx_db.write_points(json_body)
                print(r)
                return r
        except Exception as e:
            print("error "+str(e))
            logger.error("error writing influx " + str(e))
            return False

    def read(self, measurement_name, field, instance_id=None, start_time=None, end_time=None):
        logger.debug("influx read " + str(measurement_name)+ " "+ str(field)+ " "+ str(instance_id)+ " "+ str(start_time)+ " "+ str(end_time))
        data = []
        where_count = 0
        try:
            if measurement_name is not None:
                q = None
                result = None
                try:
                    q = "select " + str(field) + " from " + str(measurement_name)
                    if instance_id or start_time or end_time:
                        q += " where"
                    if instance_id:
                        q += " instance_id='" + str(instance_id) + "'"
                        where_count += 1
                    start_time = self.get_time_string(start_time)
                    if start_time:
                        if where_count > 0:
                            q += " and"
                        q += " time>='" + str(start_time) + "'"
                        where_count += 1
                    end_time = self.get_time_string(end_time)
                    if end_time:
                        if where_count > 0:
                            q += " and"
                        q += " time<='" + str(end_time) + "'"
                        where_count += 1
                    q +=";"
                    logger.info(q)
                except Exception as e:
                    logger.error("error forming read query "+str(measurement_name)+" "+str(e))
                if q:
                    result = self.influx_db.query(q)
                if result:
                    for r in result.get_points():
                        t = int(datetime.datetime.strptime(str(r["time"]), "%Y-%m-%dT%H:%M:%SZ").timestamp())
                        v = r[str(field)]
                        try:
                            v = float(v)
                        except Exception as e:
                            pass
                        if isinstance(v, str) and "," in v:
                            v = v.split(",")
                        data.append([t, v])
        except Exception as e:
            logger.error("error reading influx " + str(e) + " " + str(measurement_name))
        return data

    def get_time_string(self, time):
        t = None
        if time:
            if isinstance(time, int) or isinstance(time, float):
                t = datetime.datetime.fromtimestamp(time).strftime("%Y-%m-%dT%H:%M:%SZ")
            elif isinstance(time, datetime.datetime):
                t = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return t

    def timeseries_list_to_influx_json(self, data, measurement_name, field, instance_id):
        json_body = []
        for t, v in data:
            json_body.append({
                "measurement": measurement_name,
                "tags": {
                    "instance_id": instance_id
                },
                "time": datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": {
                    field: v
                }
            })
        print(len(json_body))
        return json_body

    def timeseries_dict_to_influx_json(self, data, measurement_name, instance_id):
        json_body = []
        for t, v in data.items():
            json_body.append({
                "measurement": measurement_name,
                "tags": {
                    "instance_id": instance_id
                },
                "time": datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": v
            })
        print(len(json_body))
        return json_body
