# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.output_source import OutputSource  # noqa: E501
from swagger_server.test import BaseTestCase


class TestControlController(BaseTestCase):
    """ControlController integration test stubs"""

    def test_delete_file_output(self):
        """Test case for delete_file_output

        Deletes the output of the framework
        """
        response = self.client.open(
            '/v1/control/file/{id}'.format(id='id_example'),
            method='DELETE',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_delete_mqtt_output(self):
        """Test case for delete_mqtt_output

        Deletes the registration output of the framework
        """
        response = self.client.open(
            '/v1/control/mqtt/{id}'.format(id='id_example'),
            method='DELETE',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_output_source_file(self):
        """Test case for output_source_file

        Get ouput of the optimization
        """
        response = self.client.open(
            '/v1/control/file/{id}'.format(id='id_example'),
            method='GET',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_output_source_mqtt(self):
        """Test case for output_source_mqtt

        Creates a new control setpoint as ouput
        """
        Output_Source = OutputSource()
        response = self.client.open(
            '/v1/control/mqtt/{id}'.format(id='id_example'),
            method='PUT',
            data=json.dumps(Output_Source),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
