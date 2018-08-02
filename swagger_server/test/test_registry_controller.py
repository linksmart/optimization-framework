# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.input_source import InputSource  # noqa: E501
from swagger_server.models.output_source import OutputSource  # noqa: E501
from swagger_server.test import BaseTestCase


class TestRegistryController(BaseTestCase):
    """RegistryController integration test stubs"""

    def test_input_source(self):
        """Test case for input_source

        Creates a new data source as input
        """
        Input_Source = InputSource()
        response = self.client.open(
            '/v1/registry/input/',
            method='POST',
            data=json.dumps(Input_Source),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_output_source(self):
        """Test case for output_source

        Creates a new data source as ouput
        """
        Output_Source = OutputSource()
        response = self.client.open(
            '/v1/registry/output/',
            method='POST',
            data=json.dumps(Output_Source),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
