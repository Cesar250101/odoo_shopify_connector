from odoo import models, api, fields, _
from odoo.exceptions import Warning,UserError
from ..model.api import API
import base64
import json
from ..unit.backend_adapter import ShopifyImportExport
from ..unit.product_importer import ShopifyProductImport
from ..unit.product_exporter import ShopifyProductExport


import logging
_logger = logging.getLogger(__name__)


class ProductMapping(models.Model):
    """ Model to store shopify id for particular product"""
    _name = 'shopify.odoo.product.template'
    _description = 'shopify.odoo.product.template'

    product_id = fields.Many2one(comodel_name='product.template',
                                 string='Product Template',
                                 ondelete='cascade',
                                 readonly=False,
                                 required=True,
                                 )

    backend_id = fields.Many2one(comodel_name='shopify.configure',
                                 string='Backend',
                                 ondelete='set null',
                                 store=True,
                                 readonly=False,
                                 required=False,
                                 )

    shopify_id = fields.Char(string='Shopify id')

class ProductProduct(models.Model):

    _inherit = 'product.product'

    shopify_id = fields.Char(string='Shopify id', store=True)


    backend_mapping = fields.One2many(comodel_name='shopify.odoo.product.product',
                                      string='Product mapping',
                                      inverse_name='product_id',
                                      readonly=False,
                                      required=False,
                                      )

class ProductProductMapping(models.Model):

    _name = 'shopify.odoo.product.product'
    _description = 'shopify.odoo.product.product'

    product_id = fields.Many2one(comodel_name='product.product',
                                 string='Product',
                                 ondelete='cascade',
                                 readonly=False,
                                 required=True,
                                 )

    backend_id = fields.Many2one(comodel_name='shopify.configure',
                                 string='Backend',
                                 ondelete='set null',
                                 store=True,
                                 readonly=False,
                                 required=False,
                                 )

    shopify_id = fields.Char(string='shopify id')


class ProductTemplate(models.Model):
    """ Models for shopify product template """
    _inherit = 'product.template'
   

    backend_mapping = fields.One2many(comodel_name='shopify.odoo.product.template',
                                      string='Product mapping',
                                      inverse_name='product_id',
                                      readonly=False,
                                      required=False,
                                      )

    backend_id = fields.Many2many(comodel_name='shopify.configure',
                                  string='Shopify Backend',
                                  store=True,
                                  readonly=False,
                                  required=True,
                                  )
    tag_ids = fields.Many2many('product.tags', string='Tags')
    shopify_id = fields.Char(string='shopify id', store=True)
    compare_at_price = fields.Float(string='Compare at Price',store=True)
    length_backend = fields.Boolean(compute='get_length')
    # shopify_img_id = fields.Char(string = "Shopify Image ID",store=True)

    @api.model
    def get_length(self):
        if len(self.backend_id) > 1:
            self.length_backend = True
        else:
            self.length_backend = False

    @api.model
    def create(self, vals):
        """ Override create method to check price before creating and export """
        if not 'list_price' in vals.keys():
            vals['list_price'] = 0
        if not 'standard_price' in vals.keys():
            vals['standard_price'] = 0
        product_id = super(ProductTemplate, self).create(vals)
        return product_id

    def write(self, vals):
        """ Override write method to export when any details is changed """
        if (self.backend_id or 'backend_id' in vals.keys()):
            if not 'list_price' in vals.keys():
                vals['list_price'] = self.list_price
            if not 'standard_price' in vals.keys():
                vals['standard_price'] = self.standard_price
            product = super(ProductTemplate, self).write(vals)
            return product
        else:
            product = super(ProductTemplate, self).write(vals)
            return product


    def importer(self, backend):
        """ import and create or update backend mapper """

        if len(self.ids)>1:
            for obj in self:
                obj.single_importer(backend)
            return

        method = 'product_import'
        arguments = [None,self]
        shopify_product_import_obj = ShopifyProductImport(backend)
        shopify_import_export_obj = ShopifyImportExport(backend)

        shopify_api = API(url=shopify_import_export_obj.location, consumer_key=shopify_import_export_obj.consumer_key,
                    consumer_secret=shopify_import_export_obj.consumer_secret, version=shopify_import_export_obj.version, shopify_api=True)
        record_data = shopify_api.get("products/count").json()
        product_count = record_data['count']

        count=0
        data = True
        product_ids = []

        res = shopify_product_import_obj.import_product(method, arguments, count)['data']

        if res:
            product_ids.extend(res['products'])

        for pro_id in product_ids:
            self.single_importer(backend, pro_id)

    def single_importer(self, backend, product_id, status=True, shopify_id=None):
        method = 'product_import'
        try:
            product_id = product_id['id']
        except:
            product_id = product_id

        mapper = self.backend_mapping.search(
            [('backend_id', '=', backend.id), ('shopify_id', '=', product_id)], limit=1)
        arguments = [product_id or None, mapper.product_id or self]

        shopify_product_import_obj = ShopifyProductImport(backend)
        res = shopify_product_import_obj.import_product(method, arguments)

        record = res['data']

        if mapper:
            shopify_product_import_obj.write_product(backend, mapper, res)
        else:
            product_template = shopify_product_import_obj.create_product(backend, mapper, res, status)

        # added because create_product fun
        mapper = self.backend_mapping.search([('backend_id', '=', backend.id), ('shopify_id', '=', product_id)], limit=1)

        if mapper and (res['status'] == 200 or res['status'] == 201):
            if 'product' in res['data']:
                result = res['data']['product']
            else:
                result = res['data']['products'][0]
            vals = {
                'shopify_id': result['id'],
                'backend_id': backend.id,
                'product_id': mapper.product_id.id,
            }

            # if result['images']:
            #     vals.update({'image_id':result['images'][0]['id']})

            mapper.product_id.backend_mapping.write(vals)

        elif (res['status'] == 200 or res['status'] == 201):
            if 'product' in res['data']:
                result = res['data']['product']
            else:
                result = res['data']['products'][0]
            vals = {
                'shopify_id': result['id'],
                'backend_id': backend.id,
                'product_id': product_template.id,
            }
            # if result['images']:
            #     vals.update({'image_id':result['images'][0]['id']})

            product_template.backend_mapping.create(vals)

    def sync_product(self):
        for backend in self.backend_id:
            self.export_product(backend)
        return

    def sync_multiple_product(self):
        for each in self:
            for backend in each.backend_id:
                each.export_product(backend)
        return

    def export_product(self, backend):

        mapper = self.backend_mapping.search(
            [('backend_id', '=', backend.id), ('product_id', '=', self.id)], limit=1)
        arguments = []
        method = 'products'

        arguments = [mapper.shopify_id or None, self]
        export = ShopifyProductExport(backend)
        res = export.export_product(method, arguments)

        if mapper and (res['status'] == 200 or res['status'] == 201):
            vals = {'product_id': self.id, 'backend_id': backend.id, 'shopify_id': res['data']['product']['id']}

            mapper.write(vals)

        elif (res['status'] == 200 or res['status'] == 201):

            vals = {'product_id': self.id, 'backend_id': backend.id, 'shopify_id': res['data']['product']['id']}

            self.backend_mapping.create(vals)

class ProductTags(models.Model):
    _name = 'product.tags'
    _description = 'Product Tags'

    name = fields.Char(string="Tag Name", required="1")

class ProductMultiImage(models.Model):
    _inherit = 'product.image'

    name = fields.Char(string= 'Image Name')

class ProductMultiImages(models.Model):

    """ Models for product images """
    _name = "product.multi.image"
    _description = 'product.multi.image'

    image = fields.Binary(string="Image")
    name = fields.Char(string="Name")
    main_img = fields.Boolean(string="Main Product Image")
    shopify_id = fields.Char(string="Shopify id")
    product_id = fields.Many2one(comodel_name='product.product',
                                 string='Product')
    position = fields.Integer(string="Position")
    src = fields.Char(string="Source")

    backend_mapping = fields.One2many(comodel_name='shopify.odoo.product.image',
                                      string='Product Image mapping',
                                      inverse_name='product_image_id',
                                      readonly=False,
                                      required=False,)
    backend_id = fields.Many2many(comodel_name='shopify.configure',
                                  string='Shopify Backend',
                                  store=True,
                                  readonly=False,
                                  required=True,
                                  )


class ProductImageMapping(models.Model):

    """ Model to store woocommerce id for particular product"""
    _name = 'shopify.odoo.product.image'
    _description = 'shopify.odoo.product.image'
    product_id = fields.Many2one(comodel_name='product.product',
                                 string='Product',
                                 ondelete='cascade',
                                 readonly=False,
                                 required=True,)
    product_image_id = fields.Many2one(comodel_name='product.multi.image',
                                       string='Product image',
                                       ondelete='cascade',
                                       readonly=False,
                                       required=True,)

    backend_id = fields.Many2one(comodel_name='shopify.configure',
                                 string='Backend',
                                 ondelete='set null',
                                 store=True,
                                 readonly=False,
                                 required=False,)

    shopify_id = fields.Char(string='Shopify Id')


class ProductAttribute(models.Model):

    _inherit = 'product.attribute'

    backend_id = fields.Many2many(comodel_name='shopify.configure',
                                  string='Backend',
                                  store=True,
                                  readonly=False,
                                  required=False,
                                  )

    backend_mapping = fields.One2many(comodel_name='shopify.odoo.attribute',
                                      string='Attribute mapping',
                                      inverse_name='attribute_id',
                                      readonly=False,
                                      required=False,
                                      )

    @api.model
    def create(self, vals):
        """ Override create method """
        backend_obj = self.env['shopify.configure']
        backend_ids = backend_obj.search([('name', '!=', None)])
        vals['backend_id'] = [[6, 0, backend_ids.ids]]
        attribute_id = super(ProductAttribute, self).create(vals)
        return attribute_id

    def write(self, vals):
        attribute = super(ProductAttribute, self).write(vals)
        return attribute



class ProductAttributeMapping(models.Model):

    _name = 'shopify.odoo.attribute'

    attribute_id = fields.Many2one(comodel_name='product.attribute',
                                   string='Product Attribute',
                                   ondelete='cascade',
                                   readonly=False,
                                   required=True,
                                   )

    backend_id = fields.Many2one(comodel_name='shopify.configure',
                                 string='Backend',
                                 ondelete='set null',
                                 store=True,
                                 readonly=False,
                                 required=False,
                                 )

    shopify_id = fields.Char(string='shopify id')


class ProductAttributeValue(models.Model):

    _inherit = 'product.attribute.value'

    backend_id = fields.Many2many(comodel_name='shopify.configure',
                                  string='Backend',
                                  store=True,
                                  readonly=False,
                                  required=False,
                                  )
    backend_mapping = fields.One2many(comodel_name='shopify.odoo.attribute.value',
                                      string='Attribute value mapping',
                                      inverse_name='attribute_value_id',
                                      readonly=False,
                                      required=False,
                                      )

    @api.model
    def create(self, vals):
        """ Override create method """
        backend_obj = self.env['shopify.configure']
        backend_ids = backend_obj.search([('name', '!=', None)])
        vals['backend_id'] = [[6, 0, backend_ids.ids]]
        attribute_value = super(ProductAttributeValue, self).create(vals)
        return attribute_value

    def write(self, vals):
        """ Override write method to export when any details is changed """
        attribute_value = super(ProductAttributeValue, self).write(vals)
        return attribute_value


class ProductAttributeValueMapping(models.Model):

    _name = 'shopify.odoo.attribute.value'

    attribute_value_id = fields.Many2one(comodel_name='product.attribute.value',
                                         string='Product Attribute Value',
                                         ondelete='cascade',
                                         readonly=False,
                                         required=True,
                                         )

    backend_id = fields.Many2one(comodel_name='shopify.configure',
                                 string='Backend',
                                 ondelete='set null',
                                 store=True,
                                 readonly=False,
                                 required=False,
                                 )

    shopify_id = fields.Char(string='shopify id')

