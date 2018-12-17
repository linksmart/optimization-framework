"""
Created on Okt 04 12:03 2018

@author: nishit
"""
import configparser
import json
import logging

import os

import time

import shutil

from IO.redisDB import RedisDB
from prediction.loadPrediction import LoadPrediction
from prediction.offlineTrain import OfflineTrain

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
                    logger.info("creating new training thread for topic " + prediction_name)
                    training_threads[key] = LoadPrediction(config, value["control_frequency"],
                                                           value["horizon_in_steps"],
                                                           prediction_name, value["topic_param"],
                                                           value["dT_in_seconds"], id, False)
                elif key in training_threads.keys() and key not in keys:
                    logger.info("stoping training thread for topic " + key)
                    training_threads[key].Stop()
                    training_threads.pop(key)
        time.sleep(1)


def clear_redis():
    logger.info("reset redis training key locks")
    training_lock_key = "training_lock"
    from IO.redisDB import RedisDB
    redisDB = RedisDB()
    try:
        redisDB.remove(training_lock_key)
    except Exception as e:
        logger.debug("key does not exist")


if __name__ == '__main__':
    config_path = "/usr/src/app/utils/ConfigFile.properties"
    if not os.path.exists(config_path):
        shutil.copyfile("/usr/src/app/config/ConfigFile.properties", config_path)
    try:
        clear_redis() #  need to relook
        config = configparser.RawConfigParser()
        config.read(config_path)
        check_training(config)
        """
        ot = OfflineTrain(horizon_in_steps=1440, num_timesteps=60, hidden_size=120, batch_size=1, num_epochs=5,
                          raw_data_file="/usr/src/app/prediction/resources/raw_data_P_Load.csv",
                          model_file_container="/usr/src/app/prediction/resources/testModel.h5",
                          model_file_container_train="/usr/src/app/prediction/resources/partTestModel.h5",
                          topic_name="P_Load", id="000111", dT_in_seconds=60, output_size=1440)
        ot.train()
        """
    except Exception as e:
        logger.error(e)
