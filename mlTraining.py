"""
Created on Okt 04 12:03 2018

@author: nishit
"""
import configparser
import json
import logging

import os

import time

from IO.redisDB import RedisDB
from prediction.loadPrediction import LoadPrediction

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

redisDB = RedisDB()

training_threads = {}

def check_training(config):
    while True:
        keys = redisDB.get_keys_for_pattern("train:*")
        if keys is not None:
            keys_union = set(training_threads.keys()).union(keys)
            for key in keys_union:
                if key not in training_threads.keys() and key in keys:
                    sub_keys = key.split(":")
                    id = sub_keys[1]
                    prediction_name = sub_keys[2]
                    value = redisDB.get(key)
                    value = json.loads(value)
                    logger.info("creating new training thread for topic "+prediction_name)
                    training_threads[key] = LoadPrediction(config, value["control_frequency"], value["horizon_in_steps"],
                                                           prediction_name, value["topic_param"], value["dT_in_seconds"], id, False)
                elif key in training_threads.keys() and key not in keys:
                    logger.info("stoping training thread for topic "+key)
                    training_threads[key].Stop()
                    training_threads.pop(key)
        time.sleep(1)

def clear_redis():
    logger.info("reset redis")
    from IO.redisDB import RedisDB
    redisDB = RedisDB()
    redisDB.reset()
    redisDB.set("time", time.time())

if __name__ == '__main__':
    try:
        clear_redis()
        config = configparser.RawConfigParser()
        data_file = os.path.join("/usr/src/app", "utils", "ConfigFile.properties")
        config.read(data_file)
        check_training(config)
    except Exception as e:
        logger.error(e)
