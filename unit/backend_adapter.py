#    Techspawn Solutions Pvt. Ltd.
#    Copyright (C) 2016-TODAY Techspawn(<http://www.Techspawn.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


from odoo import models, fields, tools, api
import logging
from ..model.api import API
from datetime import datetime
from datetime import timedelta
_logger = logging.getLogger(__name__)
from PIL import Image
import os, sys
import base64
import codecs
import io

class ShopifyImportExport(object):

    """ Models for shopify export import """

    def __init__(self, backend):
        """ Initialized all variables """
        self.backend = backend
        self.location = backend.location
        self.consumer_key = backend.consumer_key
        self.consumer_secret = backend.consumer_secret
        self.version = backend.version

   

    def importer(self, method, arguments,count=None,date=None):
        """ Import all data to shopi commerce"""
        location = self.location
        cons_key = self.consumer_key
        sec_key = self.consumer_secret
        backend= self.backend
        version = self.version
        api = API(url=location, consumer_key=cons_key,
                  consumer_secret=sec_key, version=version, shopify_api=True,timeout=100)
        res = api.get(self.get_api_method(method, arguments,count, date))

        _logger.info(
            "Import to api %s, status : %s res : %s", self.get_api_method(method, arguments,count, date), res.status_code, res.text)
        return res


    def export(self, method, result_dict, arguments):

        version = self.version
        api = API(url=self.location,
                  consumer_key=self.consumer_key,
                  consumer_secret=self.consumer_secret,
                  version=version,
                  shopify_api=True,
                  timeout=200)

        if arguments[0]:
            res = api.put(self.get_api_method(method, arguments), result_dict)
        else:
            res = api.post(self.get_api_method(method, arguments), result_dict)

        _logger.info(
            "Export to api %s, status : %s res : %s", self.get_api_method(method, arguments), res.status_code, res.text)
        return res
