from odoo import  fields, models, api, _

class SyncWizard(models.TransientModel):
    _name = "sync.multiple"

    select_backend = fields.Many2one(comodel_name='shopify.configure',
                                      string='Choose an Instance',
                                      store=True,
                                      readonly=False,
                                      required=False)

    def get_backend(self):
        prod = self.env.context.get('active_id')
        prod_id = self.env['product.template'].search([('id', '=', prod)])
        select_backend = self.select_backend
        prod_id.backend_id = select_backend

        prod_id.sync_product()

    def get_customer_backend(self):
        id_active = self.env.context.get('active_id')
        target_id = self.env['res.partner'].search([('id', '=', id_active)])
        select_backend = self.select_backend
        target_id.backend_id = select_backend

        target_id.sync_customer()

    def get_saleorder_backend(self):
        id_active = self.env.context.get('active_id')
        target_id = self.env['sale.order'].search([('id', '=', id_active)])
        select_backend = self.select_backend
        target_id.backend_id = select_backend

        target_id.sync_sale_order()


class MultipleSyncwizard(models.TransientModel):
    _name = "selective.saleorder"

    select_backend = fields.Many2one(comodel_name='shopify.configure',
                                      string='Choose an Instance',
                                      store=True,
                                      readonly=False,
                                      required=False)




