"""
Created on Okt 04 12:03 2018

@author: nishit
"""
import configparser
import json

import time

from config.configUpdater import ConfigUpdater
from prediction.machineLearning import MachineLearning
from prediction.training import Training

training_threads = {}


def check_training(config, logger, redisDB):
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
                    logger.info("creating new training thread for topic " + prediction_name)
                    training_threads[key] = Training(config, value["horizon_in_steps"], prediction_name,
                                                     value["dT_in_seconds"], id)
                    training_threads[key].start()
                elif key in training_threads.keys() and key not in keys:
                    logger.info("stoping training thread for topic " + key)
                    training_threads[key].Stop()
                    training_threads.pop(key)
        time.sleep(1)


def clear_redis(logger):
    logger.info("reset redis training key locks")
    training_lock_key = "training_lock"
    from IO.redisDB import RedisDB
    redisDB = RedisDB()
    try:
        redisDB.remove(training_lock_key)
    except Exception as e:
        logger.debug("training_lock key does not exist")
    return redisDB


if __name__ == '__main__':
    config_path = "/usr/src/app/prediction/resources/trainingConfig.properties"
    config_path_default = "/usr/src/app/config/trainingConfig.properties"
    config, logger = ConfigUpdater.get_config_and_logger("training", config_path_default, config_path)

    redisDB = clear_redis(logger)  # need to relook
    check_training(config, logger, redisDB)
