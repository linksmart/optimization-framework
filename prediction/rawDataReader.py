"""
Created on Okt 04 13:51 2018

@author: nishit
"""
import os

import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class RawDataReader:

    @staticmethod
    def read_from_file(file_path):
        try:
            if os.path.exists(file_path):
                with open(file_path) as file:
                    data = file.readlines()
                file.close()
                return data
            else:
                logger.info("File not found "+file_path)
                return []
        except Exception as e:
            logger.error(e)
        return []

    @staticmethod
    def add_formated_data(data=[]):
        new_data = []
        for row in data:
            cols = row.replace('\n', '').strip().split(",")
            dateTime = cols[0]
            cols = cols[1:]
            cols = list(map(float, cols))
            cols.insert(0, dateTime)
            new_data.append(cols)
        return new_data

    @staticmethod
    def get_raw_data(file_path, data_length):
        data = RawDataReader.read_from_file(file_path)
        if len(data) > data_length:
            data = data[-data_length:]
        return RawDataReader.add_formated_data(data)
