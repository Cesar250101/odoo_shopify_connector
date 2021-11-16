from ..model.api import API
import requests
from odoo.exceptions import Warning, UserError
from PIL import Image
from io import BytesIO
import io
import base64
import json
from odoo import models, fields, tools, api
from base64 import b64encode
from json import dumps
import logging
from ..model.api import API
from datetime import datetime
from datetime import timedelta
from .backend_adapter import ShopifyImportExport


_logger = logging.getLogger(__name__)
from odoo import http, tools
import hashlib
import os
from odoo.http import request


class ShopifyProductExport(ShopifyImportExport):

    def get_api_method(self, method, args):

        api_method = None
        if method == 'products':
            if not args[0]:
                api_method = 'products.json'
            else:
                api_method = 'products/' + str(args[0]) + '.json'
        return api_method

    def get_images(self, product):
        """ get all images of product """
        if product.image_medium:
            image = product.image_medium.decode("utf-8")
            images = {
                       "attachment":image,
                       "product_id": product.id or None,
                       "position": 1,
                       }
        else:
            images = {}
        return images

    def get_multiple_images(self,product):
        multiple_img=[]

        if product.image_medium:
            image = product.image_medium.decode("utf-8")
            images = {
                       "attachment":image,
                       "product_id": product.id or None,
                       "position": 1,
                       }
            multiple_img.append(images)
        else:
            images={}

        if product.product_image_ids:
            count=1
            for each in product.product_image_ids:
                count+=1
                image = each.image.decode("utf-8")
                images = {
                    "attachment": image,
                    "product_id": product.id or None,
                    "position": int(count),
                }
                multiple_img.append(images)
        elif product.image_medium and not product.product_image_ids:
            image = product.image_medium.decode("utf-8")
            images = {
                "attachment": image,
                "product_id": product.id or None,
                "position": 1,
            }
            multiple_img.append(images)
        else:
            multiple_img=[]
        return multiple_img

    def get_attributes(self, product):
        """ get all attributes of product """
        attributes = []
        for attr in product.attribute_line_ids:
            attributes_value = []
            for value in attr.value_ids:
                attributes_value.append(value.name)
            attributes.append({
                "name": attr.attribute_id.name or None,
                "values": attributes_value,
            })
        return attributes

    def get_product_variant(self, product):
        """ get all variant of product """

        if product.type == "product":
            product_type = "shopify"
        elif product.type == "consu":
            product_type = "null"
        else:
            product_type = "shopify"


        product_variant = []
        for var_ids in product.product_variant_ids:
            shopify_product_comb = var_ids
            attr_array = []
            # product_template_attribute_value_ids
            for attribute in shopify_product_comb.product_template_attribute_value_ids:
                attr_array.append(attribute.name)
            if len(attr_array) == 1:
                option1 = attr_array[0]
                option2 = ''
                option3 = ''
            elif len(attr_array) == 2:
                option1 = attr_array[0]
                option2 = attr_array[1]
                option3 = ''
            elif len(attr_array) == 3:
                option1 = attr_array[0]
                option2 = attr_array[1]
                option3 = attr_array[2]

            if shopify_product_comb:
                mapper = shopify_product_comb.backend_mapping.search(
                    [('backend_id', '=', self.backend.id), ('product_id', '=', shopify_product_comb.id)])
                if mapper:
                    product_variant_dict = {
                        "id": mapper.shopify_id or None,
                        # "product_id": mapper.product_id.id or None,
                        "sku": shopify_product_comb.default_code or None,
                        "weight": shopify_product_comb.weight or None,
                        'inventory_policy': 'continue',
                        "inventory_management": product_type,
                        "inventory_quantity": int(shopify_product_comb.qty_available) or None,
                        "price": shopify_product_comb.lst_price or None,
                    }
                    product_variant_dict.update(
                        {'option1': option1,
                         'option2': option2,
                         'option3': option3})
                else:
                    product_variant_dict = {
                        "sku": shopify_product_comb.default_code or None,
                        "weight": shopify_product_comb.weight or None,
                        'inventory_policy': 'continue',
                        "inventory_management": product_type,
                        "inventory_quantity": int(shopify_product_comb.qty_available) or None,
                        "price": shopify_product_comb.lst_price or None,
                    }
                    product_variant_dict.update(
                        {'option1': option1,
                         'option2': option2,
                         'option3': option3})

                product_variant.append(product_variant_dict)
        return product_variant

    def export_product(self, method, arguments):
        #status
        if arguments[1].active:
            status = 'active'
        else:
            status = 'draft' or 'archived'

        #inventory_management
        if arguments[1].type == "product":
            product_type = "shopify"
        elif arguments[1].type == "consu":
            product_type = "null"
        else:
            product_type = "shopify"

        if not arguments[0]:
            result_dict = {
                "product": {
                    'title': str(arguments[1].name) or None,
                    "body_html": arguments[1].description or '',
                    "product_type": str(arguments[1].categ_id.name),
                    'inventory_policy': 'continue',
                    "inventory_management": product_type,
                    'inventory_quantity': int(arguments[1].qty_available) or None,
                    'status': status,
                    "options": self.get_attributes(arguments[1]),
                    "image": self.get_images(arguments[1]),
                    "images": self.get_multiple_images(arguments[1]),
                }
            }
            if arguments[1].product_variant_count > 1:
                result_dict['product'].update({
                    'variants': self.get_product_variant(arguments[1]),
                })
        else:
            result_dict = {
                "product":{
                    'id': arguments[0],
                    'title': arguments[1].name or None,
                    "body_html": arguments[1].description or '',
                    "product_type": str(arguments[1].categ_id.name),
                    'inventory_policy': 'continue',
                    "inventory_management": product_type,
                    'inventory_quantity': int(arguments[1].qty_available) or None,
                    'status': status,
                    "options": self.get_attributes(arguments[1]),
                    "image": self.get_images(arguments[1]),
                    "images": self.get_multiple_images(arguments[1]),
                }
            }
            if arguments[1].product_variant_count >= 1:
                result_dict['product'].update({
                    'variants': self.get_product_variant(arguments[1]),
                })

        _logger.info("Odoo Product Export Data: %s", result_dict)

        r = self.export(method, result_dict, arguments)

        return {'status': r.status_code, 'data': r.json()}
