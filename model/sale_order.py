from odoo import models, api, fields, _
from . api import API
from odoo.exceptions import Warning,UserError
import logging
from collections import defaultdict
import base64
from ..unit.backend_adapter import ShopifyImportExport
from ..unit.sale_order_import import ShopifySaleOrderImport
from ..unit.sale_order_export import ShopifySaleOrderExport

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):

    _inherit = 'sale.order'

    shopify_payment_status = fields.Char(string="Payment Status", readonly= True)
    shopify_sale_order_number = fields.Char(string="Sale Order Number", readonly= True)
    shopify_payment_method = fields.Char(string= "Payment Method",readonly= True)
    shopify_order_id = fields.Char(string= "Shopify Sale Order ID",readonly= True)
    length_backend = fields.Boolean(compute='get_length')

    @api.model
    def get_length(self):
        if len(self.backend_id) > 1:
            self.length_backend = True
        else:
            self.length_backend = False

    @api.model
    def get_backend(self):
        return self.env['shopify.configure'].search([]).ids

    backend_id = fields.Many2many(comodel_name='shopify.configure',
                                  string='Shopify Backend',
                                  store=True,
                                  readonly=False,
                                  required=True,
                                  )

    backend_mapping = fields.One2many(comodel_name='shopify.odoo.sale.order',
                                      string='Sale Order mapping',
                                      inverse_name='order_id',
                                      readonly=False,
                                      required=False,
                                      )

    def importer(self, backend):

        if len(self.ids) > 1:
            for obj in self:
                obj.single_importer(backend)
            return

        method = 'sales_order_import'
        arguments = [None, self]
        importer = ShopifySaleOrderImport(backend)

        shopify_import_export_obj = ShopifyImportExport(backend)

        shopify_api = API(url=shopify_import_export_obj.location, consumer_key=shopify_import_export_obj.consumer_key,
                          consumer_secret=shopify_import_export_obj.consumer_secret,
                          version=shopify_import_export_obj.version, shopify_api=True)
        record_data = shopify_api.get("orders/count").json()
        order_count = record_data['count']

        count = 1

        data = True
        sale_ids = []

        res = importer.import_sales_order(method, arguments, count)['data']

        if res:
            sale_ids.extend(res['orders'])

        for sale_id in sale_ids:
            self.single_importer(backend, sale_id)

    @api.model
    def create(self, vals):
        """ Override create method to export"""
        _logger.info("create vals %s", vals)
        if 'partner_id' in vals.keys():
            vals['partner_id'] = int(vals['partner_id'])
        sales_order_id = super(SaleOrder, self).create(vals)
        return sales_order_id


    def write(self, vals):
        """ Override write method to export when any details is changed """
        _logger.info("write vals %s", vals)
        for sale_order in self:
            res = super(SaleOrder, sale_order).write(vals)
        return True

    def sync_sale_order(self):
        for backend in self.backend_id:
            self.export(backend)
        return

    def sync_multiple_sale_order(self):
        for each in self:
            for backend in each.backend_id:
                each.export(backend)
        return

    def sales_line(self, vals):
        res = self.write({'order_line': [[0, 0, vals]]})
        return True

    def single_importer(self, backend, sale_id, status=True, shopify_id=None):

        method = 'sales_order_import'


        mapper = self.backend_mapping.search(
            [('backend_id', '=', backend.id), ('shopify_id', '=', sale_id['id'])], limit=1)

        arguments = [sale_id or None, mapper.order_id or self]
        import_obj = ShopifySaleOrderImport(backend)
        res = import_obj.import_sales_order(method, arguments)

        if mapper:
            import_obj.write_sale_order(backend, mapper, res)
        else:
            sale_order_template = import_obj.create_sale_order(backend, mapper, res, status)

        try:
            partner_id = self.env['shopify.odoo.res.partner'].search(
                [('backend_id', '=', backend.id), ('shopify_id', '=', res['data']['orders'][0]['customer']['id'])])
        except:
            partner_id = False

        if mapper and (res['status'] == 200 or res['status'] == 201):
            vals = {
                'shopify_id': res['data']['orders'][0]['id'],
                'backend_id': backend.id,
                'order_id': mapper.order_id.id,
            }
            self.backend_mapping.write(vals)
        else:
            if (partner_id):
                vals = {
                    'shopify_id': res['data']['orders'][0]['id'],
                    'backend_id': backend.id,
                    'order_id': sale_order_template.id,
                }

                self.backend_mapping.create(vals)

    def export(self, backend):
        """ export and create or update backend mapper """
        if len(self.ids) > 1:
            for obj in self:
                obj.export(backend)
            return
        mapper = self.backend_mapping.search([('backend_id', '=', backend.id), ('order_id', '=', self.id)], limit=1)
        method = 'sales_order'
        arguments = [mapper.shopify_id or None, self]
        export = ShopifySaleOrderExport(backend)

        res = export.export_sales_order(method, arguments)

        if mapper and (res['status'] == 200 or res['status'] == 201):
            mapper.write(
                {'order_id': self.id, 'backend_id': backend.id, 'shopify_id': res['data']['order']['id']})
        elif (res['status'] == 200 or res['status'] == 201):
            self.backend_mapping.create(
                {'order_id': self.id, 'backend_id': backend.id, 'shopify_id': res['data']['order']['id']})

        # assign order_line_id of sp in odoo order_line of field name "backend"(means:line_item_id)
        if 'order' in res['data']:
            for index, value in enumerate(res['data']['order']['line_items']):
                self.order_line[index].backend = value['id']


class SalesOrderMapping(models.Model):

    _name = 'shopify.odoo.sale.order'

    order_id = fields.Many2one(comodel_name='sale.order',
                               string='Sale Order',
                               ondelete='cascade',
                               readonly=False,
                               required=True,
                               )

    backend_id = fields.Many2one(comodel_name='shopify.configure',
                                 string='Website',
                                 ondelete='set null',
                                 store=True,
                                 readonly=False,
                                 required=False,
                                 )
    shopify_id = fields.Char(string='shopify id')

class SalesOrderLine(models.Model):

    _inherit = 'sale.order.line'
    # backend = fields.Integer("shopify line id")
    backend = fields.Char("shopify line id")

    backend_mapping = fields.One2many(comodel_name='shopify.sale.order.line',
                                      string='Order Line mapping',
                                      inverse_name='line_item_id',
                                      readonly=False,
                                      required=False,
                                      )

class ShopifySaleOrderLine(models.Model):

    _name = 'shopify.sale.order.line'

    line_item_id = fields.Many2one(comodel_name='sale.order.line',
                               string='Sale Order line',
                               ondelete='cascade',
                               readonly=False,
                               required=True,
                               )

    backend_id = fields.Many2one(comodel_name='shopify.configure',
                                 string='Website',
                                 ondelete='set null',
                                 store=True,
                                 readonly=False,
                                 required=False,
                                 )