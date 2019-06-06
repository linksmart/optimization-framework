# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.chargers_file import ChargersFile  # noqa: F401,E501
from swagger_server.models.ess_file import ESSFile  # noqa: F401,E501
from swagger_server.models.ev_file import EvFile  # noqa: F401,E501
from swagger_server.models.generic_files import GenericFiles  # noqa: F401,E501
from swagger_server.models.global_control_file import GlobalControlFile  # noqa: F401,E501
from swagger_server.models.grid import Grid  # noqa: F401,E501
from swagger_server.models.horizons import Horizons  # noqa: F401,E501
from swagger_server.models.load_file import LoadFile  # noqa: F401,E501
from swagger_server.models.pv_file import PVFile  # noqa: F401,E501
from swagger_server.models.uncertainity_file import UncertainityFile  # noqa: F401,E501
from swagger_server import util


class FileInputSource(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, generic: GenericFiles=None, load: LoadFile=None, photovoltaic: PVFile=None, ess: ESSFile=None, grid: Grid=None, global_control: GlobalControlFile=None, horizons: Horizons=None, ev: EvFile=None, chargers: ChargersFile=None, uncertainity: UncertainityFile=None):  # noqa: E501
        """FileInputSource - a model defined in Swagger

        :param generic: The generic of this FileInputSource.  # noqa: E501
        :type generic: GenericFiles
        :param load: The load of this FileInputSource.  # noqa: E501
        :type load: LoadFile
        :param photovoltaic: The photovoltaic of this FileInputSource.  # noqa: E501
        :type photovoltaic: PVFile
        :param ess: The ess of this FileInputSource.  # noqa: E501
        :type ess: ESSFile
        :param grid: The grid of this FileInputSource.  # noqa: E501
        :type grid: Grid
        :param global_control: The global_control of this FileInputSource.  # noqa: E501
        :type global_control: GlobalControlFile
        :param horizons: The horizons of this FileInputSource.  # noqa: E501
        :type horizons: Horizons
        :param ev: The ev of this FileInputSource.  # noqa: E501
        :type ev: EvFile
        :param chargers: The chargers of this FileInputSource.  # noqa: E501
        :type chargers: ChargersFile
        :param uncertainity: The uncertainity of this FileInputSource.  # noqa: E501
        :type uncertainity: UncertainityFile
        """
        self.swagger_types = {
            'generic': GenericFiles,
            'load': LoadFile,
            'photovoltaic': PVFile,
            'ess': ESSFile,
            'grid': Grid,
            'global_control': GlobalControlFile,
            'horizons': Horizons,
            'ev': EvFile,
            'chargers': ChargersFile,
            'uncertainity': UncertainityFile
        }

        self.attribute_map = {
            'generic': 'generic',
            'load': 'load',
            'photovoltaic': 'photovoltaic',
            'ess': 'ESS',
            'grid': 'grid',
            'global_control': 'global_control',
            'horizons': 'horizons',
            'ev': 'EV',
            'chargers': 'chargers',
            'uncertainity': 'uncertainity'
        }

        self._generic = generic
        self._load = load
        self._photovoltaic = photovoltaic
        self._ess = ess
        self._grid = grid
        self._global_control = global_control
        self._horizons = horizons
        self._ev = ev
        self._chargers = chargers
        self._uncertainity = uncertainity

    @classmethod
    def from_dict(cls, dikt) -> 'FileInputSource':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The FileInputSource of this FileInputSource.  # noqa: E501
        :rtype: FileInputSource
        """
        return util.deserialize_model(dikt, cls)

    @property
    def generic(self) -> GenericFiles:
        """Gets the generic of this FileInputSource.


        :return: The generic of this FileInputSource.
        :rtype: GenericFiles
        """
        return self._generic

    @generic.setter
    def generic(self, generic: GenericFiles):
        """Sets the generic of this FileInputSource.


        :param generic: The generic of this FileInputSource.
        :type generic: GenericFiles
        """

        self._generic = generic

    @property
    def load(self) -> LoadFile:
        """Gets the load of this FileInputSource.


        :return: The load of this FileInputSource.
        :rtype: LoadFile
        """
        return self._load

    @load.setter
    def load(self, load: LoadFile):
        """Sets the load of this FileInputSource.


        :param load: The load of this FileInputSource.
        :type load: LoadFile
        """

        self._load = load

    @property
    def photovoltaic(self) -> PVFile:
        """Gets the photovoltaic of this FileInputSource.


        :return: The photovoltaic of this FileInputSource.
        :rtype: PVFile
        """
        return self._photovoltaic

    @photovoltaic.setter
    def photovoltaic(self, photovoltaic: PVFile):
        """Sets the photovoltaic of this FileInputSource.


        :param photovoltaic: The photovoltaic of this FileInputSource.
        :type photovoltaic: PVFile
        """

        self._photovoltaic = photovoltaic

    @property
    def ess(self) -> ESSFile:
        """Gets the ess of this FileInputSource.


        :return: The ess of this FileInputSource.
        :rtype: ESSFile
        """
        return self._ess

    @ess.setter
    def ess(self, ess: ESSFile):
        """Sets the ess of this FileInputSource.


        :param ess: The ess of this FileInputSource.
        :type ess: ESSFile
        """

        self._ess = ess

    @property
    def grid(self) -> Grid:
        """Gets the grid of this FileInputSource.


        :return: The grid of this FileInputSource.
        :rtype: Grid
        """
        return self._grid

    @grid.setter
    def grid(self, grid: Grid):
        """Sets the grid of this FileInputSource.


        :param grid: The grid of this FileInputSource.
        :type grid: Grid
        """

        self._grid = grid

    @property
    def global_control(self) -> GlobalControlFile:
        """Gets the global_control of this FileInputSource.


        :return: The global_control of this FileInputSource.
        :rtype: GlobalControlFile
        """
        return self._global_control

    @global_control.setter
    def global_control(self, global_control: GlobalControlFile):
        """Sets the global_control of this FileInputSource.


        :param global_control: The global_control of this FileInputSource.
        :type global_control: GlobalControlFile
        """

        self._global_control = global_control

    @property
    def horizons(self) -> Horizons:
        """Gets the horizons of this FileInputSource.


        :return: The horizons of this FileInputSource.
        :rtype: Horizons
        """
        return self._horizons

    @horizons.setter
    def horizons(self, horizons: Horizons):
        """Sets the horizons of this FileInputSource.


        :param horizons: The horizons of this FileInputSource.
        :type horizons: Horizons
        """

        self._horizons = horizons

    @property
    def ev(self) -> EvFile:
        """Gets the ev of this FileInputSource.


        :return: The ev of this FileInputSource.
        :rtype: EvFile
        """
        return self._ev

    @ev.setter
    def ev(self, ev: EvFile):
        """Sets the ev of this FileInputSource.


        :param ev: The ev of this FileInputSource.
        :type ev: EvFile
        """

        self._ev = ev

    @property
    def chargers(self) -> ChargersFile:
        """Gets the chargers of this FileInputSource.


        :return: The chargers of this FileInputSource.
        :rtype: ChargersFile
        """
        return self._chargers

    @chargers.setter
    def chargers(self, chargers: ChargersFile):
        """Sets the chargers of this FileInputSource.


        :param chargers: The chargers of this FileInputSource.
        :type chargers: ChargersFile
        """

        self._chargers = chargers

    @property
    def uncertainity(self) -> UncertainityFile:
        """Gets the uncertainity of this FileInputSource.


        :return: The uncertainity of this FileInputSource.
        :rtype: UncertainityFile
        """
        return self._uncertainity

    @uncertainity.setter
    def uncertainity(self, uncertainity: UncertainityFile):
        """Sets the uncertainity of this FileInputSource.


        :param uncertainity: The uncertainity of this FileInputSource.
        :type uncertainity: UncertainityFile
        """

        self._uncertainity = uncertainity
