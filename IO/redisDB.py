"""
Created on Aug 16 11:57 2018

@author: nishit
"""

import redis
import time

from utils_intern.messageLogger import MessageLogger

logger = MessageLogger.get_logger_parent()

class RedisDB:

    def __init__(self):
        self.redis_db = redis.StrictRedis(host="redis_S4G", port=6379, db=0)
        self.disable_persistence()

    def disable_persistence(self):
        value = self.redis_db.config_get("save")
        if len(value) > 0:
            self.redis_db.config_set("save", "")
            logger.debug("Redis persistence disabled")

    def get(self, key, default=None):
        value = self.redis_db.get(name=key)
        if value is not None:
            value = str(value, "utf-8")
            return value
        else:
            return default

    def set(self, key, value):
        self.redis_db.set(name=key, value=value)

    def remove(self, key):
        self.redis_db.delete(key)

    def add_to_list(self, key, value):
        self.redis_db.rpush(key, value)

    def get_list(self, key, start=0, end=-1):
        return self.parse_list(self.redis_db.lrange(name=key, start=start, end=end))

    def get_keys_for_pattern(self, pattern):
        return self.parse_list(self.redis_db.keys(pattern=pattern))

    def parse_list(self, blist):
        if blist is not None:
            slist = []
            for item in blist:
                slist.append(str(item, "utf-8"))
            return slist
        else:
            return None

    def reset(self):
        self.redis_db.flushall()

    def key_exists(self, key):
        return self.redis_db.exists(key)

    def get_lock(self, key, value):
        status = self.get(key, "False")
        while status is not "False":
            status = self.get(key, "False")
            time.sleep(0.5)
        if not self.key_exists(key):
            self.set(key, value)
            #logger.debug("lock granted to "+str(value))
            return True
        else:
            logger.debug("lock not granted to " + str(value))
            return False

    def release_lock(self, key, value):
        status = self.get(key, "False")
        if status == value:
            self.remove(key)
            #logger.debug("lock release from " + str(value))

    def get_start_time(self):
        return float(self.redis_db.get("time"))

    def get_bool(self, key, default=False):
        value = self.redis_db.get(name=key)
        if value is not None:
            if not isinstance(value, bool):
                value = str(value, "utf-8")
                if value == "True":
                    value = True
                elif value == "False":
                    value = False
            return value
        else:
            return default