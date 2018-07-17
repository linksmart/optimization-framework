"""
Created on Jul 16 11:10 2018

@author: nishit
"""
import uuid


class Utils:

    id = "0"

    @classmethod
    def create_and_get_ID(cls):
        id = uuid.uuid4()
        id = str(id).split("-")[4]
        cls.id = id
        return id

    @classmethod
    def get_ID(cls):
        return cls.id
