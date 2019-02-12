# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.mqtt import MQTT  # noqa: F401,E501
from swagger_server import util


class SourceOutput(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, mqtt: MQTT=None, unit: str=None):  # noqa: E501
        """SourceOutput - a model defined in Swagger

        :param mqtt: The mqtt of this SourceOutput.  # noqa: E501
        :type mqtt: MQTT
        :param unit: The unit of this SourceOutput.  # noqa: E501
        :type unit: str
        """
        self.swagger_types = {
            'mqtt': MQTT,
            'unit': str
        }

        self.attribute_map = {
            'mqtt': 'mqtt',
            'unit': 'unit'
        }

        self._mqtt = mqtt
        self._unit = unit

    @classmethod
    def from_dict(cls, dikt) -> 'SourceOutput':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The SourceOutput of this SourceOutput.  # noqa: E501
        :rtype: SourceOutput
        """
        return util.deserialize_model(dikt, cls)

    @property
    def mqtt(self) -> MQTT:
        """Gets the mqtt of this SourceOutput.


        :return: The mqtt of this SourceOutput.
        :rtype: MQTT
        """
        return self._mqtt

    @mqtt.setter
    def mqtt(self, mqtt: MQTT):
        """Sets the mqtt of this SourceOutput.


        :param mqtt: The mqtt of this SourceOutput.
        :type mqtt: MQTT
        """
        if mqtt is None:
            raise ValueError("Invalid value for `mqtt`, must not be `None`")  # noqa: E501

        self._mqtt = mqtt

    @property
    def unit(self) -> str:
        """Gets the unit of this SourceOutput.


        :return: The unit of this SourceOutput.
        :rtype: str
        """
        return self._unit

    @unit.setter
    def unit(self, unit: str):
        """Sets the unit of this SourceOutput.


        :param unit: The unit of this SourceOutput.
        :type unit: str
        """

        self._unit = unit