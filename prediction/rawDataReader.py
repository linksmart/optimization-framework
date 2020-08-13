"""
Created on Okt 04 13:51 2018

@author: nishit
"""
import datetime
import os
import time

from senml import senml

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class RawDataReader:

    @staticmethod
    def read_from_file(file_path, topic_name):
        try:
            if os.path.exists(file_path):
                with open(file_path) as file:
                    data = file.readlines()
                file.close()
                return data
            else:
                logger.info("Saved data not available "+str(topic_name))
                return []
        except Exception as e:
            logger.error(e)
        return []

    @staticmethod
    def time_conversion(time):
        time = int(time)
        if len(str(time)) > 10:
            new_t = time / (10 ** (len(str(time)) - 10))
            return new_t
        else:
            return time

    @staticmethod
    def format_data(data=[]):
        new_data = []
        doc = None
        try:
            doc = senml.SenMLDocument.from_json(data)
        except Exception as e:
            pass
        if not doc:
            try:
                meas = senml.SenMLMeasurement.from_json(data)
                doc = senml.SenMLDocument([meas])
            except Exception as e:
                pass
        if doc:
            for meas in doc.measurements:
                try:
                    n = meas.name
                    v = meas.value
                    t = meas.time
                    t = RawDataReader.time_conversion(t)
                    cols = [t,v]
                    new_data.append(cols)
                except Exception as e:
                    logger.error("Exception in formating meas " + str(e))
            return new_data
        else:
            for row in data:
                try:
                    cols = row.replace('\n', '').strip().split(",")
                    dateTime = float(cols[0])
                    cols = cols[1:]
                    cols = list(map(float, cols))
                    cols.insert(0, dateTime)
                    new_data.append(cols)
                except Exception as e:
                    logger.error("Exception in formating line "+str(row)+ " "+ str(e))
            return new_data

    @staticmethod
    def get_raw_data(file_path, topic_name, data_length=None):
        data = RawDataReader.read_from_file(file_path, topic_name)
        if data_length is not None and len(data) > data_length:
            data = data[-data_length:]
        if len(data) > 0:
            indexes = []
            for i,v in enumerate(data):
                if "inf" in str(v).lower() or "nan" in str(v).lower():
                    indexes.append(i)
            logger.debug("len indexes " + str(len(indexes)))
            indexes.sort(reverse=True)
            for index in indexes:
                data.pop(index)
        return RawDataReader.format_data(data)

    @staticmethod
    def get_raw_data_by_time(file_path, topic_name, start_time, end_time):
        #logger.debug("start time "+str(start_time)+" end time "+str(end_time))
        flag = False
        new_data = []
        if start_time < end_time:
            data = RawDataReader.read_from_file(file_path, topic_name)
            start_time = int(start_time)
            end_time = int(end_time)
            for row in data:
                try:
                    col = row.replace('\n', '').strip().split(",")
                    t = float(col[0])
                    v = float(col[1])
                    if not flag and start_time <= t:
                        flag = True
                    if flag and end_time < t:
                        break
                    if flag:
                        new_data.append([t,v])
                except Exception as e:
                    logger.error("Exception in formating line " + str(row) + " " + str(e))
        return new_data

    @staticmethod
    def save_to_file(file_path, topic_name, minute_data, max_file_size_mins=-1, overwrite=False):
        try:
            logger.info("Saving raw data to file " + str(file_path))
            if overwrite:
                old_data = []
            else:
                old_data = RawDataReader.read_from_file(file_path, topic_name)
            for item in minute_data:
                line = ','.join(map(str, item[:2])) + "\n"
                old_data.append(line)
            if max_file_size_mins > 0:
                old_data = old_data[-max_file_size_mins:]
            update_data = []
            for i, line in enumerate(old_data):
                c = line.count(",")
                if c == 2:
                    s = line.split(",")
                    m = s[1]
                    mv = m[:-12]
                    mt = m[-12:]
                    l1 = [float(s[0]), float(mv)]
                    l1 = ','.join(map(str, l1[:2])) + "\n"
                    l2 = [float(mt), float(s[2].replace("\n", ""))]
                    l2 = ','.join(map(str, l2[:2])) + "\n"
                    update_data.append([i, l1, l2])
                elif c != 1:
                    update_data.append([i, None, None])
            shift = 0
            for d in update_data:
                if d[1] is not None and d[2] is not None:
                    old_data.pop(d[0] + shift)
                    old_data.insert(d[0] + shift, d[1])
                    old_data.insert(d[0] + shift + 1, d[2])
                    shift += 1
                else:
                    old_data.pop(d[0] + shift)
                    shift -= 1
            with open(file_path, 'w+') as file:
                file.writelines(old_data)
            file.close()
            return []
        except Exception as e:
            logger.error("failed to save_to_file " + str(e))
            return minute_data

    @staticmethod
    def del_file(file_path, topic_name):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error("failed to del_to_file " + str(e)+" "+str(topic_name))

    @staticmethod
    def removed_data_before_timestamp(file_path, topic_name, lastest_timestamp):
        data = RawDataReader.get_raw_data_by_time(file_path, topic_name, lastest_timestamp, time.time())
        RawDataReader.save_to_file(file_path, topic_name, data, overwrite=True)

    @staticmethod
    def save_to_influx(influxdb, topic_name, minute_data, id):
        try:
            logger.info("Saving raw data to influx " + str(topic_name))
            json_body = influxdb.timeseries_list_to_influx_json(minute_data, topic_name, "raw", id)
            if not influxdb.write(json_body):
                return minute_data
            else:
                return []
        except Exception as e:
            logger.error("failed to save_to_influx " + str(e))
            return minute_data

    @staticmethod
    def get_raw_data_influx(influxdb, topic_name, id, data_length=None):
        start_time = None
        if data_length:
            start_time = datetime.datetime.now() - datetime.timedelta(minutes=data_length+720) # half day extra
        data = influxdb.read(topic_name, "raw", instance_id=id, start_time=start_time)
        if data_length is not None and len(data) > data_length:
            data = data[-data_length:]
        if len(data) > 0:
            indexes = []
            for i, v in enumerate(data):
                if "inf" in str(v).lower() or "nan" in str(v).lower():
                    indexes.append(i)
            logger.debug("len indexes " + str(len(indexes)))
            indexes.sort(reverse=True)
            for index in indexes:
                data.pop(index)
        return data

    @staticmethod
    def get_raw_data_by_time_influx(influxdb, topic_name, start_time, end_time, id):
        new_data = []
        if start_time < end_time:
            new_data = influxdb.read(topic_name, "raw", instance_id=id, start_time=start_time, end_time=end_time)
        return new_data