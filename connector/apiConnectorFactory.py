"""
Created on Mär 27 12:16 2019

@author: nishit
"""
from connector.priceConnector import PriceConnector


class ApiConnectorFactory:

    @staticmethod
    def get_api_connector(name, url, config, house):
        if "price" in name:
            return PriceConnector(url, config, house)