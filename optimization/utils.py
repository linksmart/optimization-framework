"""
Created on Jul 16 11:10 2018

@author: nishit
"""
import uuid

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Utils(metaclass=Singleton):

    def create_and_get_ID(self):
        self.id = str(uuid.uuid4()).split("-")[4]
        return self.id

    def get_ID(self):
        return self.id
