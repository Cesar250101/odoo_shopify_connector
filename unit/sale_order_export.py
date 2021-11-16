import requests
import logging
from ..model.api import API
from datetime import datetime
from datetime import timedelta
# from . backend_adapter import WpImportExport
from ..unit.backend_adapter import ShopifyImportExport

_logger = logging.getLogger(__name__)


class ShopifySaleOrderExport(ShopifyImportExport):

    def get_api_method(self, method, args):
        """ get api for sale order and values"""

        api_method = None
        if method == 'sales_order':
            if not args[0]:
                api_method = 'orders.json'
            else:
                api_method = 'orders/' + str(args[0]) + '.json'
        return api_method

    # def get_tax_lines(self):


    def get_order_lines(self, order_lines):
        """ get all order lines """
        lines = []
        if order_lines:
            for order_line in order_lines:
                product_id = order_line.product_id.product_tmpl_id.backend_mapping.search(
                    [('backend_id', '=', self.backend.id),
                     ('product_id', '=', order_line.product_id.product_tmpl_id.id)])
                variation_id = order_line.product_id.backend_mapping.search(
                    [('backend_id', '=', self.backend.id), ('product_id', '=', order_line.product_id.id)])

                if order_line.qty_delivered == 0:
                    fulfillment_status = "unshipped"
                elif order_line.qty_delivered == order_line.product_uom_qty:
                    fulfillment_status = "fulfilled"
                elif order_line.qty_delivered < order_line.product_uom_qty:
                    fulfillment_status = "unfulfilled"
                else:
                    fulfillment_status = "unshipped"

                if product_id:
                    if order_line.backend:
                        lines.append({"id": order_line.backend,
                                      "product_id": int(product_id.shopify_id),
                                      "title": str(order_line.name),
                                      "variant_id": int(variation_id.shopify_id),
                                      "quantity": int(order_line.product_uom_qty) or '',
                                      "price": str(order_line.price_unit),
                                      # "fulfillment_status": fulfillment_status,
                                      "taxable": True,
                                      "tax_lines":[
                                           {
                                              "price":str(order_line.price_unit*(order_line.tax_id.amount/100)),
                                              "price_set":{
                                                 "shop_money":{
                                                    "amount":str(order_line.price_unit*(order_line.tax_id.amount/100)),
                                                    "currency_code":"USD"
                                                 },
                                                 "presentment_money":{
                                                    "amount":str(order_line.price_unit*(order_line.tax_id.amount/100)),
                                                    "currency_code":"USD"
                                                 }
                                              },
                                              "rate":0.1,
                                              "title":str(order_line.tax_id.name) or '',
                                           }
                                        ],
                                      })
                    else:
                        lines.append({
                                      "product_id": int(product_id.shopify_id),
                                      "title": str(order_line.name),
                                      "variant_id": int(variation_id.shopify_id),
                                      "quantity": int(order_line.product_uom_qty) or '',
                                      "price": str(order_line.price_unit),
                                      # "fulfillment_status": fulfillment_status,
                                      "taxable": True,
                                      "tax_lines":[
                                           {
                                              "price":str(order_line.price_unit*(order_line.tax_id.amount/100)),
                                              "price_set":{
                                                 "shop_money":{
                                                    "amount":str(order_line.price_unit*(order_line.tax_id.amount/100)),
                                                    "currency_code":"USD"
                                                 },
                                                 "presentment_money":{
                                                    "amount":str(order_line.price_unit*(order_line.tax_id.amount/100)),
                                                    "currency_code":"USD"
                                                 }
                                              },
                                              "rate":0.1,
                                              "title":str(order_line.tax_id.name) or '',
                                           }
                                        ],
                                      })
        print("Lines----",lines)
        return lines

    def export_sales_order(self, method, arguments):
        """ Export sale order data"""

        _logger.debug("Start calling shopify api %s", method)

        status = ''
        if arguments[1].state == 'done':
            status = 'paid'
        elif arguments[1].state == 'draft':
            status = 'pending'
        elif arguments[1].state == 'sale':
            status = 'authorized'
        elif arguments[1].state == 'cancel':
            status = 'voided'


        customer_shopify_id = arguments[1].partner_id.backend_mapping.search(
            [('backend_id', '=', self.backend.id), ('customer_id', '=', arguments[1].partner_id.id)], limit=1)

        # update order
        if arguments[0]:
            if customer_shopify_id.shopify_id:
                result_dict = {
                    "order": {
                    "id": arguments[0],
                    "financial_status": status,
                    "email": arguments[1].partner_id.email or '',
                    "phone": arguments[1].partner_id.phone or None,
                    "note": arguments[1].note or '',
                    'customer':{ 'id': int(customer_shopify_id.shopify_id),
                                 "email": arguments[1].partner_id.email or '',
                                 "first_name": arguments[1].partner_id.name or '',
                                 "last_name": arguments[1].partner_id.last_name_1 or '',
                                 },

                    "billing_address": {"first_name": arguments[1].partner_id.name or '',
                                "last_name": arguments[1].partner_id.last_name_1 or '',
                                # "company": arguments[1].partner_id.company or '',
                                "address1": arguments[1].partner_id.street or '',
                                "address2": arguments[1].partner_id.street2 or '',
                                "city": arguments[1].partner_id.city or '',
                                "province_code": arguments[1].partner_id.state_id.code or '',
                                "zip": arguments[1].partner_id.zip or '',
                                "country_code": arguments[1].partner_id.country_id.code or '',
                                "phone": arguments[1].partner_id.phone or '',
                                },
                    "shipping_address": {"first_name": arguments[1].partner_id.name or '',
                                 "last_name": arguments[1].partner_id.last_name_1 or '',
                                 "address1": arguments[1].partner_id.street or '',
                                 "address2": arguments[1].partner_id.street2 or '',
                                 "city": arguments[1].partner_id.city or '',
                                 "province_code": arguments[1].partner_id.state_id.code or '',
                                 "zip": arguments[1].partner_id.zip or '',
                                 "country_code": arguments[1].partner_id.country_id.code or '',
                                 "phone": arguments[1].partner_id.phone or '',
                                 },
                    "line_items": self.get_order_lines(arguments[1].order_line),
                    "total_price": arguments[1].amount_total,
                    "subtotal_price": arguments[1].amount_untaxed,
                    # "fulfillment_status": "null",
                    # "tax_lines": [],
                }}

            else:
                result_dict = {
                    "order": {
                        "id": arguments[0],
                        "financial_status": status,
                        "note": arguments[1].note or '',
                        'customer': {"first_name": arguments[1].partner_id.name or '',
                                      "last_name": arguments[1].partner_id.last_name_1 or '',
                                      "email": arguments[1].partner_id.email or '',
                                      "phone": arguments[1].partner_id.phone or None,
                                     },

                        "billing_address": {"first_name": arguments[1].partner_id.name or '',
                                    "last_name": arguments[1].partner_id.last_name_1 or '',
                                    # "company": arguments[1].partner_id.company or '',
                                    "address1": arguments[1].partner_id.street or '',
                                    "address2": arguments[1].partner_id.street2 or '',
                                    "city": arguments[1].partner_id.city or '',
                                    "province_code": arguments[1].partner_id.state_id.code or '',
                                    "zip": arguments[1].partner_id.zip or '',
                                    "country_code": arguments[1].partner_id.country_id.code or '',
                                    "phone": arguments[1].partner_id.phone or '',
                                    },
                        "shipping_address": {"first_name": arguments[1].partner_id.name or '',
                                     "last_name": arguments[1].partner_id.last_name_1 or '',
                                     "address1": arguments[1].partner_id.street or '',
                                     "address2": arguments[1].partner_id.street2 or '',
                                     "city": arguments[1].partner_id.city or '',
                                     "province_code": arguments[1].partner_id.state_id.code or '',
                                     "zip": arguments[1].partner_id.zip or '',
                                     "country_code": arguments[1].partner_id.country_id.code or '',
                                     "phone": arguments[1].partner_id.phone or '',
                                     },
                        "line_items": self.get_order_lines(arguments[1].order_line),
                        "total_price": arguments[1].amount_total,
                        "subtotal_price": arguments[1].amount_untaxed,
                        # "fulfillment_status": "null",
                        # "tax_lines": [],
                    }}
        # create new order
        else:
            if customer_shopify_id.shopify_id:
                result_dict = {
                    "order": {
                    "financial_status": status,
                    "note": arguments[1].note or '',
                    "email": arguments[1].partner_id.email or '',
                    "phone": arguments[1].partner_id.phone or None,
                    'customer':{ 'id': int(customer_shopify_id.shopify_id),
                                 "email": arguments[1].partner_id.email or '',
                                 "first_name": arguments[1].partner_id.name or '',
                                 "last_name": arguments[1].partner_id.last_name_1 or ''
                                 },

                    "billing_address": {"first_name": arguments[1].partner_id.name or '',
                                "last_name": arguments[1].partner_id.last_name_1 or '',
                                # "company": arguments[1].partner_id.company or '',
                                "address1": arguments[1].partner_id.street or '',
                                "address2": arguments[1].partner_id.street2 or '',
                                "city": arguments[1].partner_id.city or '',
                                "province_code": arguments[1].partner_id.state_id.code or '',
                                "zip": arguments[1].partner_id.zip or '',
                                "country_code": arguments[1].partner_id.country_id.code or '',
                                "phone": arguments[1].partner_id.phone or '',
                                },
                    "shipping_address": {"first_name": arguments[1].partner_id.name or '',
                                 "last_name": arguments[1].partner_id.last_name_1 or '',
                                 "address1": arguments[1].partner_id.street or '',
                                 "address2": arguments[1].partner_id.street2 or '',
                                 "city": arguments[1].partner_id.city or '',
                                 "province_code": arguments[1].partner_id.state_id.code or '',
                                 "zip": arguments[1].partner_id.zip or '',
                                 "country_code": arguments[1].partner_id.country_id.code or '',
                                 "phone": arguments[1].partner_id.phone or '',
                                 },
                    "line_items": self.get_order_lines(arguments[1].order_line),
                    "total_price": arguments[1].amount_total,
                    "subtotal_price": arguments[1].amount_untaxed,
                    # "fulfillment_status": "null",
                    # "tax_lines": [],
                }}

            else:
                result_dict = {
                    "order": {
                        "financial_status": status,
                        "note": arguments[1].note or '',
                        'customer': {"first_name": arguments[1].partner_id.name or '',
                                      "last_name": arguments[1].partner_id.last_name_1 or '',
                                      "email": arguments[1].partner_id.email or '',
                                     "phone": arguments[1].partner_id.phone or None,
                                     },

                        "billing_address": {"first_name": arguments[1].partner_id.name or '',
                                    "last_name": arguments[1].partner_id.last_name_1 or '',
                                    # "company": arguments[1].partner_id.company or '',
                                    "address1": arguments[1].partner_id.street or '',
                                    "address2": arguments[1].partner_id.street2 or '',
                                    "city": arguments[1].partner_id.city or '',
                                    "province_code": arguments[1].partner_id.state_id.code or '',
                                    "zip": arguments[1].partner_id.zip or '',
                                    "country_code": arguments[1].partner_id.country_id.code or '',
                                    "phone": arguments[1].partner_id.phone or '',
                                    },
                        "shipping_address": {"first_name": arguments[1].partner_id.name or '',
                                     "last_name": arguments[1].partner_id.last_name_1 or '',
                                     "address1": arguments[1].partner_id.street or '',
                                     "address2": arguments[1].partner_id.street2 or '',
                                     "city": arguments[1].partner_id.city or '',
                                     "province_code": arguments[1].partner_id.state_id.code or '',
                                     "zip": arguments[1].partner_id.zip or '',
                                     "country_code": arguments[1].partner_id.country_id.code or '',
                                     "phone": arguments[1].partner_id.phone or '',
                                     },
                        "line_items": self.get_order_lines(arguments[1].order_line),
                        "total_price": arguments[1].amount_total,
                        "subtotal_price": arguments[1].amount_untaxed,
                        # "fulfillment_status": "null",
                        # "tax_lines": [],
                    }}

        r = self.export(method, result_dict, arguments)

        return {'status': r.status_code, 'data': r.json()}