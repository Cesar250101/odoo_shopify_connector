from odoo import models, api, fields, _
from odoo.exceptions import Warning,UserError
from . api import API
from ..unit.backend_adapter import ShopifyImportExport


class sp_configure(models.Model):

    """ Models for Shopify configuration """
    _name = "shopify.configure"
    _description = 'Shopify Backend Configuration'

    connectivity = fields.Boolean(string="Connectivity", default=True)
    date_creation = fields.Date('Created Date', required=True, default=fields.Date.today())
    name = fields.Char(string='Instance Name')
    location = fields.Char("Location")
    consumer_key = fields.Char("Consumer key")
    consumer_secret = fields.Char("Consumer Secret")
    verify_ssl = fields.Boolean("Verify SSL")
    version = fields.Selection([('2020-01', '2020-01'),('2020-04', '2020-04'),('2020-07', '2020-07'),('2020-10', '2020-10')], 'Version')
    warehouse = fields.Many2one(comodel_name='stock.location', string='Warehouse',
                                ondelete='set null',
                                store=True,
                                readonly=False,
                                required=False)
    pricelist = fields.Selection([])
    publish_in_website = fields.Boolean("Publish in Website?")


    def test_connection(self):
        """ Test connection with the given url """
        location = self.location
        consumer_key = self.consumer_key
        consumer_secret = self.consumer_secret
        version = self.version
        shopify_api = API(url=location, consumer_key=consumer_key,
                    consumer_secret=consumer_secret, version=version, shopify_api=True)
        result = shopify_api.get("products.json")
        if result.status_code == 404:
            raise UserError("Enter Valid url")
        msg = ''
        if result.status_code != 200:
            msg = result.json()['errors'] + '\nError Code: ' + \
                str(result.status_code)
            raise UserError(msg)
        else:
            message_id = self.env['message.wizard'].create({'message': _("Great! Connection Successful")})
            return {
                'name': _('Successful'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'message.wizard',
                # pass the id
                'res_id': message_id.id,
                'target': 'new'
            }
        return True

    def import_product(self):

        """Import all the product of particular backend"""
        product_obj = self.env['product.template']
        product_obj.importer(self)
        return True

    def export_products(self):
        """ Export all the products of particular backend """
        all_products = self.env['product.template'].search(
            [('backend_id', '=', self.id)])
        export = ShopifyImportExport(self)
        for product in all_products:
            product.export_product(self)
        return True

    def import_customer(self):
        """Import all the customers of particular backend"""
        customer_obj = self.env['res.partner']
        customer_obj.importer(self)
        return True

    def export_customers(self):
        all_customers = self.env['res.partner'].search([('backend_id','=',self.id)])
        for customer in all_customers:
            customer.export(self)
        return True

    def export_so(self):
        all_sales_orders = self.env['sale.order'].search(
            [('backend_id', '=', self.id)])
        for sales_order in all_sales_orders:
            sales_order.export(self)
        return True

    def import_sale_order(self):
        sale_order_obj = self.env['sale.order']
        sale_order_obj.importer(self)
        return True

    def cron_so_import(self):
        """ set a cron for importing SO"""
        try:
            connectors = self.env['shopify.configure'].search([])
            print("Connector=============", connectors)
            for connector in connectors:
                obj = connector
                obj.import_sale_order()
                # break
            # obj.import_sale_order()
            # obj.import_customer()
        except:
            pass

    def cron_so_export(self):
        """ set a cron for importing SO"""
        try:
            connectors = self.env['shopify.configure'].search([])
            print("Connector=============",connectors)
            for connector in connectors:
                obj = connector
                obj.export_so()
                # break
            # obj.export_so()
        except:
            pass


class MessageWizard(models.TransientModel):
    _name = 'message.wizard'

    message = fields.Text('Message', required=True)

    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}
