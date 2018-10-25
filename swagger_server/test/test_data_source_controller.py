# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.file_input_source import FileInputSource  # noqa: E501
from swagger_server.models.mqtt_input_source import MQTTInputSource  # noqa: E501
from swagger_server.test import BaseTestCase


class TestDataSourceController(BaseTestCase):
    """DataSourceController integration test stubs"""

    def test_delete_data_source_all(self):
        """Test case for delete_data_source_all

        Deletes all loaded data
        """
        response = self.client.open(
            '/v1/data_source/{id}'.format(id='id_example'),
            method='DELETE',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_delete_file_registry(self):
        """Test case for delete_file_registry

        Deletes the loaded data
        """
        response = self.client.open(
            '/v1/data_source/file/{id}'.format(id='id_example'),
            method='DELETE',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_delete_mqtt_registry(self):
        """Test case for delete_mqtt_registry

        Deletes the loaded data
        """
        response = self.client.open(
            '/v1/data_source/mqtt/{id}'.format(id='id_example'),
            method='DELETE',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_file_input_put(self):
        """Test case for file_input_put

        Submits data to the framework
        """
        dataset = FileInputSource()
        response = self.client.open(
            '/v1/data_source/file/{id}'.format(id='id_example'),
            method='PUT',
            data=json.dumps(dataset),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_file_input_source(self):
        """Test case for file_input_source

        Creates a new data source as input
        """
        File_Input_Source = FileInputSource()
        response = self.client.open(
            '/v1/data_source/file',
            method='POST',
            data=json.dumps(File_Input_Source),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_data_source_values(self):
        """Test case for get_data_source_values

        Receives data from the framework
        """
        response = self.client.open(
            '/v1/data_source/file/{id}'.format(param_name='param_name_example', id='id_example'),
            method='GET',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_mqtt_input_put(self):
        """Test case for mqtt_input_put

        Submits data to the framework
        """
        dataset = MQTTInputSource()
        response = self.client.open(
            '/v1/data_source/mqtt/{id}'.format(id='id_example'),
            method='PUT',
            data=json.dumps(dataset),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_mqtt_input_source(self):
        """Test case for mqtt_input_source

        Creates a new mqtt data source as input
        """
        MQTT_Input_Source = MQTTInputSource()
        response = self.client.open(
            '/v1/data_source/mqtt',
            method='POST',
            data=json.dumps(MQTT_Input_Source),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
