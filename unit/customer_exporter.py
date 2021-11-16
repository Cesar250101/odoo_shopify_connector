import requests
import logging
from ..model.api import API
from datetime import datetime
from datetime import timedelta
from ..unit.backend_adapter import ShopifyImportExport

_logger = logging.getLogger(__name__)


class ShopifyCustomerExport(ShopifyImportExport):

    def get_api_method(self, method, args):

        api_method = None
        if method == 'customer':
            if not args[0]:
                api_method = 'customers.json/'
            else:
                api_method = 'customers/' + str(args[0]) + '.json'
        return api_method

    def export_customer(self, method, arguments):

        _logger.debug("Start calling Shopify api %s", method)


        if not arguments[0]:
            result_dict = {
                'customer':{
                "email": arguments[1].email or '',
                "first_name": arguments[1].first_name_1 or '',
                "last_name": arguments[1].last_name_1 or '',
                "phone": arguments[1].phone,
                "verified_email": True,
                "addresses":[
                    {
                        "address1": arguments[1].street or '',
                        "city": arguments[1].city or '',
                        "province_code": arguments[1].state_id.code or None,
                        'province':arguments[1].state_id.name or '',
                        "phone": arguments[1].phone or None,
                        "zip": arguments[1].zip or '',
                        "last_name": arguments[1].last_name_1 or '',
                        "first_name": arguments[1].first_name_1 or '',
                        "country_code": arguments[1].country_id.code or None
                    }
                    ]
                }
            }
        else:
            result_dict = {
                'customer': {
                    "id": arguments[1].id,
                    "email": arguments[1].email or '',
                    "first_name": arguments[1].first_name_1 or '',
                    "last_name": arguments[1].last_name_1 or '',
                    "phone": arguments[1].phone,
                    "verified_email": True,
                    "addresses": [
                        {
                            'id': arguments[1].backend_mapping.shopify_address_id or None,
                            "address1": arguments[1].street or '',
                            "city": arguments[1].city or '',
                            "province_code": arguments[1].state_id.code or None,
                            'province': arguments[1].state_id.name or '',
                            "phone": arguments[1].phone or None,
                            "zip": arguments[1].zip or None,
                            "last_name": arguments[1].last_name_1 or '',
                            "first_name": arguments[1].first_name_1 or '',
                            "country_code": arguments[1].country_id.code or None
                        }
                    ]
                }
            }

        res = self.export(method, result_dict, arguments)

        if res:
            res_dict = res.json()
        else:
            res_dict = res.json()
        return {'status': res.status_code, 'data': res_dict or {}}
