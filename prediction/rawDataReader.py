"""
Created on Okt 04 13:51 2018

@author: nishit
"""
import os

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
    def get_raw_data(file_path, data_length, topic_name):
        data = RawDataReader.read_from_file(file_path, topic_name)
        if len(data) > data_length:
            data = data[-data_length:]
        return RawDataReader.format_data(data)
