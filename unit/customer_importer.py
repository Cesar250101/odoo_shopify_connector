from odoo.tools import config

import requests
import logging
from ..model.api import API
from datetime import datetime
from datetime import timedelta
from ..unit.backend_adapter import ShopifyImportExport
_logger = logging.getLogger(__name__)

class ShopifyCustomerImport(ShopifyImportExport):

	def get_api_method(self, method, args, count=None,date=None):
		""" get api for customer"""

		api_method = None
		if method == 'customer_import':
			if not args[0]:
				api_method = 'customers.json'
			else:
				api_method = 'customers/' + str(args[0]) + ".json"
		return api_method

	def import_customer(self,method,arguments,count=None,date=None):
		"""Import Customer data"""
		_logger.debug("Start calling Shopify api %s", method)
		result = {}
		res = self.importer(method, arguments,count=None,date=None)
		try:
			if 'false' or 'true' or 'null'in res.content:
				result = res.content.decode('utf-8')
				result=result.replace(
					'false', 'False')
				result = result.replace('true', 'True')
				result = result.replace('null', 'False')
				result = eval(result)
			else:
				result = eval(res.content)
		except:
			_logger.error("api.call(%s, %s) failed", method, arguments)
			raise
		else:
			_logger.debug("api.call(%s, %s) returned %s ",
						  method, arguments, result)

		return {'status': res.status_code, 'data': result or {}}

	def create_customer(self,backend,mapper,res,status=True):

		if (res['status'] == 200 or res['status'] == 201):

			if 'default_address' in res['data']['customer']:
				bill_country_id = mapper.env['res.partner'].country_id.search([('code', '=', res['data']['customer']['default_address']['country_code'])])
				bill_country_id = bill_country_id.id
				bill_state_id = mapper.env['res.partner'].state_id.search(
					[('code', '=', res['data']['customer']['default_address']['province_code']), ('country_id', '=', bill_country_id)])
			else:
				bill_country_id = ''
				bill_state_id = ''

			child_ids = []

			shipping_details = {
				'type': 'delivery',
				'name': res['data']['customer']['first_name'] + res['data']['customer']['last_name'] or '',
				'first_name_1':res['data']['customer']['first_name'] or '',
				'last_name_1': res['data']['customer']['last_name'] or '',
				'street': res['data']['customer']['default_address']['address1'] if 'default_address' in res['data']['customer'] else '',
				'street2': res['data']['customer']['default_address']['address2'] if 'default_address' in res['data']['customer'] else '',
				'city': res['data']['customer']['default_address']['city'] if 'default_address' in res['data']['customer'] else '',
				#'state_id': bill_state_id.id or None,
				'state_id': bill_state_id or None,
				'zip': res['data']['customer']['default_address']['zip'] if 'default_address' in res['data']['customer'] else '',
				'country_id': bill_country_id or None,
			}
			child_ids.append((0, 0, shipping_details))
			billing_details = {
				'type': 'invoice',
				'name': res['data']['customer']['first_name'] + res['data']['customer']['last_name'] or '',
				'first_name_1': res['data']['customer']['first_name'] or '',
				'last_name_1': res['data']['customer']['last_name'] or '',
				'street': res['data']['customer']['default_address']['address1'] if 'default_address' in res['data'][
					'customer'] else '',
				'street2': res['data']['customer']['default_address']['address2'] if 'default_address' in res['data'][
					'customer'] else '',
				'city': res['data']['customer']['default_address']['city'] if 'default_address' in res['data'][
					'customer'] else '',
				#'state_id': bill_state_id.id or None,
				'state_id': bill_state_id or None,
				'zip': res['data']['customer']['default_address']['zip'] if 'default_address' in res['data'][
					'customer'] else '',
				'country_id': bill_country_id or None,
			}
			child_ids.append((0, 0, billing_details))


			vals={
			'backend_id' : [[6,0,[backend.id]]],
			'first_name_1': res['data']['customer']['first_name'],
			'last_name_1': res['data']['customer']['last_name'],
			'name': str(res['data']['customer']['first_name'])+ " " + str(res['data']['customer']['last_name']) or '',
			'phone':res['data']['customer']['phone'] or None,
			'email' : res['data']['customer']['email'] or '',
			'street': res['data']['customer']['default_address']['address1'] if 'default_address' in res['data']['customer'] else '',
			'street2': res['data']['customer']['default_address']['address2'] if 'default_address' in res['data']['customer'] else '',
			'city':  res['data']['customer']['default_address']['city'] if 'default_address' in res['data']['customer'] else '',
			'zip': res['data']['customer']['default_address']['zip'] if 'default_address' in res['data']['customer'] else '',
			#'state_id': bill_state_id.id or None,
			'state_id': bill_state_id or None,
			'country_id':bill_country_id or None,
			'child_ids': None if child_ids == [] else child_ids,
			
			}
			
			res_partner = mapper.customer_id.create(vals)
			
			return res_partner

	def write_customer(self,backend,mapper,res):


		if 'default_address' in res['data']['customer']:
			bill_country_id = mapper.env['res.partner'].country_id.search(
				[('code', '=', res['data']['customer']['default_address']['country_code'])])
			bill_country_id = bill_country_id.id
			bill_state_id = mapper.env['res.partner'].state_id.search(
				[('code', '=', res['data']['customer']['default_address']['province_code']),
				 ('country_id', '=', bill_country_id)])
		else:
			bill_country_id = ''
			bill_state_id = ''


		shopify_child_ids = []

		if not mapper.search([('shopify_address_id','=',res['data']['customer']['default_address']['id'])]):

			shipping_details = {
				'type': 'delivery',
				'name': res['data']['customer']['first_name'] + res['data']['customer']['last_name'] or '',
				'first_name_1': res['data']['customer']['first_name'] or '',
				'last_name_1': res['data']['customer']['last_name'] or '',
				'street': res['data']['customer']['default_address']['address1'] if 'default_address' in res['data'][
					'customer'] else '',
				'street2': res['data']['customer']['default_address']['address2'] if 'default_address' in res['data'][
					'customer'] else '',
				'city': res['data']['customer']['default_address']['city'] if 'default_address' in res['data'][
					'customer'] else '',
				#'state_id': bill_state_id.id or None,
				'state_id': bill_state_id or None,
				'zip': res['data']['customer']['default_address']['zip'] if 'default_address' in res['data'][
					'customer'] else '',
				'country_id': bill_country_id or None,
			}
			shopify_child_ids.append((0, 0, shipping_details))
			billing_details = {
				'type': 'invoice',
				'name': res['data']['customer']['first_name'] + res['data']['customer']['last_name'] or '',
				'first_name_1': res['data']['customer']['first_name'] or '',
				'last_name_1': res['data']['customer']['last_name'] or '',
				'street': res['data']['customer']['default_address']['address1'] if 'default_address' in res['data'][
					'customer'] else '',
				'street2': res['data']['customer']['default_address']['address2'] if 'default_address' in res['data'][
					'customer'] else '',
				'city': res['data']['customer']['default_address']['city'] if 'default_address' in res['data'][
					'customer'] else '',
				#'state_id': bill_state_id.id or None,
				'state_id': bill_state_id or None,
				'zip': res['data']['customer']['default_address']['zip'] if 'default_address' in res['data'][
					'customer'] else '',
				'country_id': bill_country_id or None,
			}
			shopify_child_ids.append((0, 0, billing_details))
		else:
			shopify_child_ids=[]


		vals={
		'backend_id' : [[6,0,[backend.id]]],
		'name': str(res['data']['customer']['first_name'])+ " " + str(res['data']['customer']['last_name']) or '',
		'first_name_1': res['data']['customer']['first_name'],
		'last_name_1': res['data']['customer']['last_name'],
		'phone': res['data']['customer']['phone'] or None,
		'email' : res['data']['customer']['email'] or '',
		'street': res['data']['customer']['default_address']['address1'] if 'default_address' in res['data']['customer'] else '',
		'street2': res['data']['customer']['default_address']['address2'] if 'default_address' in res['data']['customer'] else '',
		'city': res['data']['customer']['default_address']['city'] if 'default_address' in res['data']['customer'] else '',
		'zip': res['data']['customer']['default_address']['zip'] if 'default_address' in res['data']['customer'] else '',
		#'state_id': bill_state_id.id or None,
		'state_id': bill_state_id or None,
		'country_id': bill_country_id or None,
		}
		if shopify_child_ids:
			vals.update({'child_ids': shopify_child_ids})

		mapper.customer_id.write(vals)