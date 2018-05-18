# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.source import Source  # noqa: F401,E501
from swagger_server import util


class ESSOutput(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, p_ess_output: Source=None):  # noqa: E501
        """ESSOutput - a model defined in Swagger

        :param p_ess_output: The p_ess_output of this ESSOutput.  # noqa: E501
        :type p_ess_output: Source
        """
        self.swagger_types = {
            'p_ess_output': Source
        }

        self.attribute_map = {
            'p_ess_output': 'P_ESS_Output'
        }

        self._p_ess_output = p_ess_output

    @classmethod
    def from_dict(cls, dikt) -> 'ESSOutput':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The ESS_Output of this ESSOutput.  # noqa: E501
        :rtype: ESSOutput
        """
        return util.deserialize_model(dikt, cls)

    @property
    def p_ess_output(self) -> Source:
        """Gets the p_ess_output of this ESSOutput.

        Setting power of the ESS  # noqa: E501

        :return: The p_ess_output of this ESSOutput.
        :rtype: Source
        """
        return self._p_ess_output

    @p_ess_output.setter
    def p_ess_output(self, p_ess_output: Source):
        """Sets the p_ess_output of this ESSOutput.

        Setting power of the ESS  # noqa: E501

        :param p_ess_output: The p_ess_output of this ESSOutput.
        :type p_ess_output: Source
        """
        if p_ess_output is None:
            raise ValueError("Invalid value for `p_ess_output`, must not be `None`")  # noqa: E501

        self._p_ess_output = p_ess_output
