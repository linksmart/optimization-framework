import json

from IO.redisDB import RedisDB

parameters = json.dumps(
                        {"control_frequency": 60, "horizon_in_steps": 24,
                         "topic_param": None, "dT_in_seconds": 3600})
redisDB = RedisDB()
redisDB.set("train:" + "asdf" + ":" + "P_Load", parameters)