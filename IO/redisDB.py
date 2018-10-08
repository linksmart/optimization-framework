"""
Created on Aug 16 11:57 2018

@author: nishit
"""
import logging

import redis

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class RedisDB:

    def __init__(self):
        self.redis_db = redis.StrictRedis(host="redis_S4G", port=6379, db=0)

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