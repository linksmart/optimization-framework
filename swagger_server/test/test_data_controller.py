# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.dataset import Dataset  # noqa: E501
from swagger_server.test import BaseTestCase


class TestDataController(BaseTestCase):
    """DataController integration test stubs"""

    def test_get_data_in(self):
        """Test case for get_data_in

        Receives data from the framework
        """
        dataset = Dataset()
        response = self.client.open(
            '/v1/data/{id}'.format(id='id_example'),
            method='GET',
            data=json.dumps(dataset),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_load_data_in(self):
        """Test case for load_data_in

        Submits load data to the framework
        """
        dataset = None
        response = self.client.open(
            '/v1/data/load/{id}'.format(id='id_example'),
            method='POST',
            data=json.dumps(dataset),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_pv_data_in(self):
        """Test case for pv_data_in

        Submits PV data to the framework
        """
        dataset = None
        response = self.client.open(
            '/v1/data/pv/{id}'.format(id='id_example'),
            method='POST',
            data=json.dumps(dataset),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
