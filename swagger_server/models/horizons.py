# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.meta_horizon import MetaHorizon  # noqa: F401,E501
from swagger_server import util


class Horizons(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, meta: MetaHorizon=None):  # noqa: E501
        """Horizons - a model defined in Swagger

        :param meta: The meta of this Horizons.  # noqa: E501
        :type meta: MetaHorizon
        """
        self.swagger_types = {
            'meta': MetaHorizon
        }

        self.attribute_map = {
            'meta': 'meta'
        }

        self._meta = meta

    @classmethod
    def from_dict(cls, dikt) -> 'Horizons':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Horizons of this Horizons.  # noqa: E501
        :rtype: Horizons
        """
        return util.deserialize_model(dikt, cls)

    @property
    def meta(self) -> MetaHorizon:
        """Gets the meta of this Horizons.


        :return: The meta of this Horizons.
        :rtype: MetaHorizon
        """
        return self._meta

    @meta.setter
    def meta(self, meta: MetaHorizon):
        """Sets the meta of this Horizons.


        :param meta: The meta of this Horizons.
        :type meta: MetaHorizon
        """

        self._meta = meta
