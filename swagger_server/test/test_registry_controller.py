# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.datainput import Datainput  # noqa: E501
from swagger_server.test import BaseTestCase


class TestRegistryController(BaseTestCase):
    """RegistryController integration test stubs"""

    def test_change_input_channel_by_id(self):
        """Test case for change_input_channel_by_id

        Change the parameters of a data source by id
        """
        name = Datainput()
        response = self.client.open(
            '/v1/registry/data_input/{id}'.format(id=789),
            method='POST',
            data=json.dumps(name),
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_set_input_channel(self):
        """Test case for set_input_channel

        Creates a new data source as input
        """
        setInputSource = Datainput()
        response = self.client.open(
            '/v1/registry/data_input',
            method='POST',
            data=json.dumps(setInputSource),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
