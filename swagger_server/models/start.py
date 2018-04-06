# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class Start(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, frequency: int=None, solver_name: str=None):  # noqa: E501
        """Start - a model defined in Swagger

        :param frequency: The frequency of this Start.  # noqa: E501
        :type frequency: int
        :param solver_name: The solver_name of this Start.  # noqa: E501
        :type solver_name: str
        """
        self.swagger_types = {
            'frequency': int,
            'solver_name': str
        }

        self.attribute_map = {
            'frequency': 'frequency',
            'solver_name': 'solver_name'
        }

        self._frequency = frequency
        self._solver_name = solver_name

    @classmethod
    def from_dict(cls, dikt) -> 'Start':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Start of this Start.  # noqa: E501
        :rtype: Start
        """
        return util.deserialize_model(dikt, cls)

    @property
    def frequency(self) -> int:
        """Gets the frequency of this Start.


        :return: The frequency of this Start.
        :rtype: int
        """
        return self._frequency

    @frequency.setter
    def frequency(self, frequency: int):
        """Sets the frequency of this Start.


        :param frequency: The frequency of this Start.
        :type frequency: int
        """
        if frequency is None:
            raise ValueError("Invalid value for `frequency`, must not be `None`")  # noqa: E501

        self._frequency = frequency

    @property
    def solver_name(self) -> str:
        """Gets the solver_name of this Start.


        :return: The solver_name of this Start.
        :rtype: str
        """
        return self._solver_name

    @solver_name.setter
    def solver_name(self, solver_name: str):
        """Sets the solver_name of this Start.


        :param solver_name: The solver_name of this Start.
        :type solver_name: str
        """
        if solver_name is None:
            raise ValueError("Invalid value for `solver_name`, must not be `None`")  # noqa: E501

        self._solver_name = solver_name
