import logging

# import xmlrpclib
from collections import defaultdict
# from odoo.addons.queue_job.job import job
import base64
from odoo import models, fields, api, _
from ..unit.customer_importer import ShopifyCustomerImport
from ..unit.customer_exporter import ShopifyCustomerExport
from ..unit.backend_adapter import ShopifyImportExport
from ..model.api import API
from odoo.exceptions import Warning
from odoo.exceptions import Warning,UserError



_logger = logging.getLogger(__name__)


class Customer(models.Model):

    _inherit = 'res.partner'

    first_name_1 = fields.Char(string='First Name ')
    last_name_1 = fields.Char(string='Last Name')

    @api.model
    def get_backend(self):
        return self.env['shopify.configure'].search([]).ids

    backend_id = fields.Many2many(comodel_name='shopify.configure',
                                  string='backend',
                                  store=True,
                                  readonly=False,
                                  required=True,
                                  )

    backend_mapping = fields.One2many(comodel_name='shopify.odoo.res.partner',
                                      string='Customer mapping',
                                      inverse_name='customer_id',
                                      readonly=False,
                                      required=False,
                                      )

    length_backend = fields.Boolean(compute='get_length')

    @api.model
    def get_length(self):
        if len(self.backend_id) > 1:
            self.length_backend = True
        else:
            self.length_backend = False


    @api.model
    def create(self, vals):
        """ Override create method """
        customer_id = super(Customer, self).create(vals)
        return customer_id

    def write(self, vals):
        """ Override write method to export customers when any details is changed """
        customer = super(Customer, self).write(vals)
        return customer

    def importer(self, backend):
        """ import and create or update backend mapper """
        if len(self.ids)>1:
            for obj in self:
                obj.single_importer(backend)
            return

        method = 'customer_import'
        arguments = [None,self]
        importer = ShopifyCustomerImport(backend)

        shopify_import_export_obj = ShopifyImportExport(backend)

        shopify_api = API(url=shopify_import_export_obj.location, consumer_key=shopify_import_export_obj.consumer_key,
                          consumer_secret=shopify_import_export_obj.consumer_secret,
                          version=shopify_import_export_obj.version, shopify_api=True)
        record_data = shopify_api.get("customers/count").json()
        customer_count = record_data['count']

        count = 0

        data = True
        customer_ids = []

        res = importer.import_customer(method, arguments, count)['data']
        if res:
            customer_ids.extend(res['customers'])

        for customer_id in customer_ids:
            self.single_importer(backend, customer_id)

    def single_importer(self,backend,customer_id,status=True,shopify_id=None):
        method = 'customer_import'
        try:
            customer_id = customer_id['id']
        except:
            customer_id = customer_id

        mapper = self.backend_mapping.search(
            [('backend_id', '=', backend.id), ('shopify_id', '=', customer_id)], limit=1)

        arguments = [customer_id or None,mapper.customer_id or self]
        importer = ShopifyCustomerImport(backend)
        res = importer.import_customer(method, arguments)


        record = res['data']

        if mapper:
            importer.write_customer(backend,mapper,res)

        else:
            res_partner = importer.create_customer(backend,mapper,res,status)

        if mapper and (res['status'] == 200 or res['status'] == 201):

            vals = {
                'shopify_id' : res['data']['customer']['id'],
                'backend_id' : backend.id,
                'customer_id' : mapper.customer_id.id,
                'shopify_address_id':res['data']['customer']['default_address']['id'] if 'default_address' in res['data']['customer'] else '',
                
                
            }
            self.backend_mapping.write(vals)
        elif (res['status'] == 200 or res['status'] == 201):
            try: 
                vals = {
                    'shopify_id' : res['data']['customer']['id'],
                    'backend_id' : backend.id,
                    'customer_id' : res_partner.id,
                    'shopify_address_id': res['data']['customer']['default_address']['id'],
                }
            except:
                vals = {
                    'shopify_id' : res['data']['customer']['id'],
                    'backend_id' : backend.id,
                    'customer_id' : res_partner.id,
                }

            self.backend_mapping.create(vals)

    def sync_customer(self):
        for backend in self.backend_id:
            self.export(backend)
        return

    def sync_multiple_customer(self):
        for each in self:
            for backend in each.backend_id:
                each.export(backend)
        return

    def export(self, backend):
        """ export customer details, save username and create or update backend mapper """
        if len(self.ids)>1:
            for obj in self:
                obj.export(backend)
            return

        mapper = self.backend_mapping.search(
            [('backend_id', '=', backend.id), ('customer_id', '=', self.id)], limit=1)
        method = 'customer'
        arguments = [mapper.shopify_id or None, self]

        export = ShopifyCustomerExport(backend)

        res = export.export_customer(method, arguments)

        if mapper and (res['status'] == 200 or res['status'] == 201):
            mapper.write(
                {'customer_id': self.id, 'backend_id': backend.id, 'shopify_id': res['data']['customer']['id']})
        elif (res['status'] == 200 or res['status'] == 201):
            self.backend_mapping.create(
                {'customer_id': self.id, 'backend_id': backend.id, 'shopify_id': res['data']['customer']['id']})

class CustomerMapping(models.Model):

    _name = 'shopify.odoo.res.partner'


    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        ondelete='cascade',
        readonly=False,
        required=True,
    )

    backend_id = fields.Many2one(
        comodel_name='shopify.configure',
        string='Website',
        ondelete='set null',
        store=True,
        readonly=False,
        required=False,
    )

    shopify_id = fields.Char(string='Shopify id')
    shopify_address_id = fields.Char(string='Address ID')

