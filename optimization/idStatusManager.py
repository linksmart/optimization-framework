"""
Created on Mai 10 16:21 2019

@author: nishit
"""
import json
import os

import time

from utils_intern.constants import Constants
from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class IDStatusManager:

    @staticmethod
    def read_file():
        path = "/usr/src/app/optimization/resources/ids_status.txt"
        data = []
        if os.path.exists(path):
            with open(path, "r") as f:
                data = f.readlines()
        return data

    @staticmethod
    def write_file(data):
        path = "/usr/src/app/optimization/resources/ids_status.txt"
        data = IDStatusManager.remove_duplicate_ids(data)
        with open(path, "w+") as f:
            f.writelines(data)

    @staticmethod
    def remove_duplicate_ids(data):
        new_data = []
        if isinstance(data, str):
            old_data = IDStatusManager.read_file()
            json_data = json.loads(data)
            id = json_data["id"]
            for s in old_data:
                if id not in s:
                    new_data.append(s)
            new_data.append(data)
        elif isinstance(data, list):
            d = {}
            for s in data:
                j = json.loads(s)
                d[j["id"]] = s
            for k, v in d.items():
                new_data.append(v)
        return new_data

    @staticmethod
    def instances_to_restart(redisDB):
        old_ids = []
        stopped_ids = []
        try:
            if redisDB.get_lock(Constants.lock_key, "start"):
                data = IDStatusManager.read_file()
                if len(data) > 0:
                    for s in data:
                        a = s.replace("\n", "")
                        if "repetition\": -9" in a:
                            stopped_ids.append(s)
                        elif float(redisDB.get_start_time()) > float(a[a.find("\"ztarttime\": ") + 13:-1]):
                            old_ids.append(s)
                    for s in old_ids:
                        if s in data:
                            data.remove(s)
                    IDStatusManager.write_file(data)
        except Exception as e:
            logger.error("error reading ids file " + str(e))
        finally:
            redisDB.release_lock(Constants.lock_key, "start")
        return old_ids, stopped_ids

    @staticmethod
    def number_of_active_ids(redisDB):
        num = 0
        try:
            if redisDB.get_lock(Constants.lock_key, "start"):
                data = IDStatusManager.read_file()
                num = 0
                for s in data:
                    if "repetition\": -9" not in s:
                        num += 1
        except Exception as e:
            logger.error("error reading ids file " + str(e))
        finally:
            redisDB.release_lock(Constants.lock_key, "start")
        return num

    @staticmethod
    def number_of_active_ids_redis(redisDB):
        num = 0
        keys = redisDB.get_keys_for_pattern(Constants.id_meta + ":*")
        if keys is not None:
            for key in keys:
                value = redisDB.get(key)
                value = json.loads(value)
                if value["repetition"] != -9:
                    num += 1
        return num

    @staticmethod
    def persist_id(id, start, meta_data, redisDB):
        if not redisDB.get_bool("kill_signal", default=False):
            logger.info("persist id called with "+str(start)+ " for id "+str(id))
            try:
                if redisDB.get_lock(Constants.lock_key, id):
                    if start:
                        redisDB.set(Constants.id_meta + ":" + id, json.dumps(meta_data))
                        data = json.dumps(meta_data,sort_keys=True,separators=(', ', ': '))+"\n"
                        IDStatusManager.write_file(data)
                    else:
                        data = IDStatusManager.read_file()
                        lines = []
                        if len(data) > 0:
                            for s in data:
                                if id in s:
                                    lines.append(s)
                            for line in lines:
                                if line is not None and line in data:
                                    i = data.index(line)
                                    line = json.loads(line.replace("\n", ""))
                                    line["repetition"] = -9
                                    data[i] = json.dumps(line, sort_keys=True, separators=(', ', ': ')) + "\n"
                                    #data.remove(line)
                                    redisDB.set(Constants.id_meta + ":" + id, json.dumps(line))
                            IDStatusManager.write_file(data)
            except Exception as e:
                logger.error("error persisting id " + id + " " + str(start) + " " + str(e))
            finally:
                redisDB.release_lock(Constants.lock_key, id)
        else:
            logger.info("Since it is a kill signal we do not persist stop data to ids_status")

    @staticmethod
    def update_count(repetition, id, redisDB):
        st = time.time()
        if repetition > 0:
            try:
                if redisDB.get_lock(Constants.lock_key, id):
                    data = IDStatusManager.read_file()
                    if len(data) > 0:
                        line = None
                        for s in data:
                            if id in s and "repetition\": -1" not in s:
                                line = s
                                break
                        if line is not None:
                            i = data.index(line)
                            line = json.loads(line.replace("\n", ""))
                            line["repetition"] -= 1
                            data[i] = json.dumps(line, sort_keys=True, separators=(', ', ': ')) + "\n"
                            IDStatusManager.write_file(data)
            except Exception as e:
                logger.error("error updating count in file " + str(e))
            finally:
                redisDB.release_lock(Constants.lock_key, id)
        st = int(time.time() - st)
        return st

    @staticmethod
    def num_of_required_pyro_mip_servers(redisDB):
        num = 0
        try:
            if redisDB.get_lock(Constants.lock_key, "start"):
                data = IDStatusManager.read_file()
                for row in data:
                    if "stochastic" in row:
                        j = json.loads(row)
                        if j["optimization_type"] == "stochastic":
                            num += 5
                        else:
                            num += 1
                    else:
                        num +=1
        except Exception as e:
            logger.error("error reading ids file " + str(e))
        finally:
            redisDB.release_lock(Constants.lock_key, "start")
        return num

    @staticmethod
    def num_of_required_pyro_mip_servers_redis(redisDB):
        num = 0
        keys = redisDB.get_keys_for_pattern(Constants.id_meta + ":*")
        if keys is not None:
            for key in keys:
                value = redisDB.get(key)
                value = json.loads(value)
                if value is not None and "repetition" in value.keys() and "optimization_type" in value.keys():
                    if value["repetition"] != -9:
                        if value["optimization_type"] == "stochastic":
                            num += 5
                        else:
                            num += 1
        return num