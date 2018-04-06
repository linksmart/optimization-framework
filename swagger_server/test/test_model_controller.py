# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.model import Model  # noqa: E501
from swagger_server.models.model_url import ModelUrl  # noqa: E501
from swagger_server.test import BaseTestCase


class TestModelController(BaseTestCase):
    """ModelController integration test stubs"""

    def test_optimization_model(self):
        """Test case for optimization_model

        Mathematical model for the optimization solver
        """
        upModel = Model()
        response = self.client.open(
            '/v1/model',
            method='POST',
            data=json.dumps(upModel),
            content_type='text/plain')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_optimization_model_url(self):
        """Test case for optimization_model_url

        Url for the mathematical model for the optimization solver
        """
        upModelUrl = ModelUrl()
        response = self.client.open(
            '/v1/model/url',
            method='POST',
            data=json.dumps(upModelUrl),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
