# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.model import Model  # noqa: E501
from swagger_server.models.model_answer import ModelAnswer  # noqa: E501
from swagger_server.models.model_url import ModelUrl  # noqa: E501
from swagger_server.test import BaseTestCase


class TestModelsController(BaseTestCase):
    """ModelsController integration test stubs"""

    def test_delete_models(self):
        """Test case for delete_models

        Deletes the desired model of the framework
        """
        response = self.client.open(
            '/v1/models/{name}'.format(name='name_example'),
            method='DELETE',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_delete_models_all(self):
        """Test case for delete_models_all

        Deletes all models of the framework
        """
        response = self.client.open(
            '/v1/models',
            method='DELETE',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_models_in(self):
        """Test case for get_models_in

        Fetches all installed models in the framework
        """
        response = self.client.open(
            '/v1/models',
            method='GET',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_optimization_model(self):
        """Test case for optimization_model

        Mathematical model for the optimization solver
        """
        upModel = Model()
        response = self.client.open(
            '/v1/models/upload/{name}'.format(name='name_example'),
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
            '/v1/models/upload/url',
            method='POST',
            data=json.dumps(upModelUrl),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
