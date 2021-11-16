import logging
from collections import defaultdict
import base64
from odoo import models, fields, api, _
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)


class Tax(models.Model):

    _inherit = 'account.tax'

    tax_state_id = fields.Many2one(
        "res.country.state", string='State', ondelete='restrict')
    tax_country_id = fields.Many2one(
        "res.country", string='Country', ondelete='restrict')
    city = fields.Char('city')
    backend_id = fields.Many2many(comodel_name='shopify.configure',
                                  string='Shopify Backend',
                                  store=True,
                                  readonly=False,
                                  required=False,
                                  )
    backend_mapping = fields.One2many(comodel_name='shopify.odoo.tax',
                                      string='Tax mapping',
                                      inverse_name='tax_id',
                                      readonly=False,
                                      required=False,
                                      )

class TaxMapping(models.Model):

    _name = 'shopify.odoo.tax'

    tax_id = fields.Many2one(comodel_name='account.tax',
                             string='Tax',
                             ondelete='cascade',
                             readonly=False,
                             required=True,
                             )

    backend_id = fields.Many2one(comodel_name='wordpress.configure',
                                 string='Backend',
                                 ondelete='set null',
                                 store=True,
                                 readonly=False,
                                 required=False,
                                 )

    shopify_id = fields.Char(string='Shopify id')