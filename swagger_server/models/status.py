# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class Status(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, repetition: int=None, control_frequency: int=None, horizon_in_steps: int=None, model_name: str=None, solver: str=None, d_t_in_seconds: int=None, status: str=None, start_time: float=None, id: str=None):  # noqa: E501
        """Status - a model defined in Swagger

        :param repetition: The repetition of this Status.  # noqa: E501
        :type repetition: int
        :param control_frequency: The control_frequency of this Status.  # noqa: E501
        :type control_frequency: int
        :param horizon_in_steps: The horizon_in_steps of this Status.  # noqa: E501
        :type horizon_in_steps: int
        :param model_name: The model_name of this Status.  # noqa: E501
        :type model_name: str
        :param solver: The solver of this Status.  # noqa: E501
        :type solver: str
        :param d_t_in_seconds: The d_t_in_seconds of this Status.  # noqa: E501
        :type d_t_in_seconds: int
        :param status: The status of this Status.  # noqa: E501
        :type status: str
        :param start_time: The start_time of this Status.  # noqa: E501
        :type start_time: float
        :param id: The id of this Status.  # noqa: E501
        :type id: str
        """
        self.swagger_types = {
            'repetition': int,
            'control_frequency': int,
            'horizon_in_steps': int,
            'model_name': str,
            'solver': str,
            'd_t_in_seconds': int,
            'status': str,
            'start_time': float,
            'id': str
        }

        self.attribute_map = {
            'repetition': 'repetition',
            'control_frequency': 'control_frequency',
            'horizon_in_steps': 'horizon_in_steps',
            'model_name': 'model_name',
            'solver': 'solver',
            'd_t_in_seconds': 'dT_in_seconds',
            'status': 'status',
            'start_time': 'start_time',
            'id': 'id'
        }

        self._repetition = repetition
        self._control_frequency = control_frequency
        self._horizon_in_steps = horizon_in_steps
        self._model_name = model_name
        self._solver = solver
        self._d_t_in_seconds = d_t_in_seconds
        self._status = status
        self._start_time = start_time
        self._id = id

    @classmethod
    def from_dict(cls, dikt) -> 'Status':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Status of this Status.  # noqa: E501
        :rtype: Status
        """
        return util.deserialize_model(dikt, cls)

    @property
    def repetition(self) -> int:
        """Gets the repetition of this Status.


        :return: The repetition of this Status.
        :rtype: int
        """
        return self._repetition

    @repetition.setter
    def repetition(self, repetition: int):
        """Sets the repetition of this Status.


        :param repetition: The repetition of this Status.
        :type repetition: int
        """

        self._repetition = repetition

    @property
    def control_frequency(self) -> int:
        """Gets the control_frequency of this Status.


        :return: The control_frequency of this Status.
        :rtype: int
        """
        return self._control_frequency

    @control_frequency.setter
    def control_frequency(self, control_frequency: int):
        """Sets the control_frequency of this Status.


        :param control_frequency: The control_frequency of this Status.
        :type control_frequency: int
        """

        self._control_frequency = control_frequency

    @property
    def horizon_in_steps(self) -> int:
        """Gets the horizon_in_steps of this Status.


        :return: The horizon_in_steps of this Status.
        :rtype: int
        """
        return self._horizon_in_steps

    @horizon_in_steps.setter
    def horizon_in_steps(self, horizon_in_steps: int):
        """Sets the horizon_in_steps of this Status.


        :param horizon_in_steps: The horizon_in_steps of this Status.
        :type horizon_in_steps: int
        """

        self._horizon_in_steps = horizon_in_steps

    @property
    def model_name(self) -> str:
        """Gets the model_name of this Status.


        :return: The model_name of this Status.
        :rtype: str
        """
        return self._model_name

    @model_name.setter
    def model_name(self, model_name: str):
        """Sets the model_name of this Status.


        :param model_name: The model_name of this Status.
        :type model_name: str
        """

        self._model_name = model_name

    @property
    def solver(self) -> str:
        """Gets the solver of this Status.


        :return: The solver of this Status.
        :rtype: str
        """
        return self._solver

    @solver.setter
    def solver(self, solver: str):
        """Sets the solver of this Status.


        :param solver: The solver of this Status.
        :type solver: str
        """

        self._solver = solver

    @property
    def d_t_in_seconds(self) -> int:
        """Gets the d_t_in_seconds of this Status.


        :return: The d_t_in_seconds of this Status.
        :rtype: int
        """
        return self._d_t_in_seconds

    @d_t_in_seconds.setter
    def d_t_in_seconds(self, d_t_in_seconds: int):
        """Sets the d_t_in_seconds of this Status.


        :param d_t_in_seconds: The d_t_in_seconds of this Status.
        :type d_t_in_seconds: int
        """

        self._d_t_in_seconds = d_t_in_seconds

    @property
    def status(self) -> str:
        """Gets the status of this Status.


        :return: The status of this Status.
        :rtype: str
        """
        return self._status

    @status.setter
    def status(self, status: str):
        """Sets the status of this Status.


        :param status: The status of this Status.
        :type status: str
        """

        self._status = status

    @property
    def start_time(self) -> float:
        """Gets the start_time of this Status.


        :return: The start_time of this Status.
        :rtype: float
        """
        return self._start_time

    @start_time.setter
    def start_time(self, start_time: float):
        """Sets the start_time of this Status.


        :param start_time: The start_time of this Status.
        :type start_time: float
        """

        self._start_time = start_time

    @property
    def id(self) -> str:
        """Gets the id of this Status.


        :return: The id of this Status.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id: str):
        """Sets the id of this Status.


        :param id: The id of this Status.
        :type id: str
        """

        self._id = id
