# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.start import Start  # noqa: E501
from swagger_server.test import BaseTestCase


class TestCommandController(BaseTestCase):
    """CommandController integration test stubs"""

    def test_framework_start(self):
        """Test case for framework_start

        Command for starting the framework
        """
        startOFW = Start()
        response = self.client.open(
            '/v1/command/start/{id}'.format(id='id_example'),
            method='PUT',
            data=json.dumps(startOFW),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_framework_stop(self):
        """Test case for framework_stop

        Command for stoping the framework
        """
        response = self.client.open(
            '/v1/command/stop/{id}'.format(id='id_example'),
            method='PUT',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
