# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.input_source import InputSource  # noqa: E501
from swagger_server.models.output_source import OutputSource  # noqa: E501
from swagger_server.test import BaseTestCase


class TestRegistryController(BaseTestCase):
    """RegistryController integration test stubs"""

    def test_load_source(self):
        """Test case for load_source

        Creates a new data source as input
        """
        InputSource = InputSource()
        response = self.client.open(
            '/v1/registry/input/',
            method='POST',
            data=json.dumps(InputSource),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_output_source(self):
        """Test case for output_source

        Creates a new data source as ouput
        """
        OutputSource = OutputSource()
        response = self.client.open(
            '/v1/registry/output/',
            method='POST',
            data=json.dumps(OutputSource),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
