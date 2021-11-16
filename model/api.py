# -*- coding: utf-8 -*-

"""
Shopify API Class
"""

__title__ = "shopify-api"

from requests import request
from json import dumps as jsonencode
# from . oauth import OAuth
import json
import base64

class API(object):

    """ API Class """

    def __init__(self, url, consumer_key, consumer_secret, **kwargs):
        """ Initialise variables """
        self.url = url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.shopify_api = kwargs.get("shopify_api", False)
        self.version = kwargs.get("version", "2020-10")
        self.is_ssl = self.__is_ssl()
        self.timeout = kwargs.get("timeout", 3600)
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.query_string_auth = kwargs.get("query_string_auth", False)

    def __is_ssl(self):
        """ Check if url use HTTPS """
        return self.url.startswith("https")

    def __get_url(self, endpoint):
        """ Get URL for requests """
        url = self.url
        api = "api"
        #version = self.version
        version="2021-10"

        if url.endswith("/") is False:
            url = "%s/" % url

        if self.shopify_api:
            api = "api"        
        
        return "%s%s/%s/%s" % (url, api, version, endpoint)

    def __request(self, method, endpoint, data):
        """ Do requests """
        url = self.__get_url(endpoint)
        auth = None
        params = {}
        headers = {
            "user-agent": "ShopifyPythonAPI/4.0.0 Python/3.6.7",
            "content-type": "application/json;charset=utf-8",
            "accept": "application/json"
        }

        if self.is_ssl is True and self.query_string_auth is False:
            auth = (self.consumer_key, self.consumer_secret)
        elif self.is_ssl is True and self.query_string_auth is True:
            params = {
                "consumer_key": self.consumer_key,
                "consumer_secret": self.consumer_secret
            }

        if data is not None:
            data = jsonencode(data, ensure_ascii=False).encode('utf-8')

        return request(
            method=method,
            url=url,
            verify=self.verify_ssl,
            auth=auth,
            params=params,
            data=data,
            timeout=self.timeout,
            headers=headers
        )

    def get(self, endpoint):
        """ Get requests """
        return self.__request("GET", endpoint, None)

    def post(self, endpoint, data):
        """ POST requests """
        return self.__request("POST", endpoint, data)

    def put(self, endpoint, data):
        """ PUT requests """
        return self.__request("PUT", endpoint, data)

    def delete(self, endpoint):
        """ DELETE requests """
        return self.__request("DELETE", endpoint, None)

    def options(self, endpoint):
        """ OPTIONS requests """
        return self.__request("OPTIONS", endpoint, None)
