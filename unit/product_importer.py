import re
import requests
import logging
from ..model.api import API
from datetime import datetime
from datetime import timedelta
from PIL import Image
import requests
from io import BytesIO
import io
import base64
from ..unit.backend_adapter import ShopifyImportExport

_logger = logging.getLogger(__name__)


class ShopifyProductImport(ShopifyImportExport):
    """ Models for shopify product ixport """

    def get_api_method(self, method, args, count=None,date=None):
        """ get api for product"""
        api_method = None
        if method == 'product_import':
            if not args[0]:
                api_method = 'products.json'
                # api_method = 'products.json'
            elif args[0] and isinstance(args[0], int):
                api_method = 'products/' + str(args[0]) + '.json'
            else:
                api_method = 'products/' + str(args[0]['id']) + '.json'

        return api_method

    def import_product(self, method, arguments, count=None,date=None):
        """Import product data"""
        _logger.debug("Start calling Shopify api %s", method)
        result = {}

        res = self.importer(method, arguments,count,date)
        try:
            if 'false' or 'true' or 'null' in res.content:
                result = res.content.decode('utf-8')
                result = result.replace(
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

    def create_product(self, backend, mapper, res, status=True):
        if (res['status'] == 200 or res['status'] == 201):

            if 'product' in res['data']:
                result = res['data']['product']
            else:
                result = res['data']['products'][0]

            bkend_id = mapper.backend_id.search([('id', '=', backend.id)])

            #publish
            website_published = result['published_scope']

            # images
            images = []
            if result['images']:
                for img in result['images']:
                    image = base64.b64encode(requests.get(img['src'].replace('\/', '/')).content)
                    name = (img['src'].replace('\/', '/').split('?')[0]).split('/')[-1]

                    img_id = mapper.env['product.image'].search([('name', '=', name)]).id
                    if not img_id:
                        images.append((0, 0, {'name': name, 'image': image,
                                            'product_tmpl_id': mapper.product_id.id}))
                    else:
                        pass

                img = base64.b64encode(
                    requests.get(result['images'][0]['src'].replace('\/', '/')).content)
            else:
                img = ''

            # tags
            if result['tags']:
                shopify_tags = result['tags'].split(',')
                shopify_tag_ids = []
                for tag in shopify_tags:
                    tag_id = mapper.env['product.tags'].search([('name', '=', tag)]).id
                    if not tag_id:
                        create_tag_id = mapper.env['product.tags'].create({'name': tag})
                        tag_id = create_tag_id.id
                        shopify_tag_ids.append(tag_id)
                    else:
                        shopify_tag_ids.append(tag_id)
            else:
                shopify_tag_ids = []

            #product_attributes
            if result['options']:
                attributes_value = []
                for attribute in result['options']:
                    attribute_id = mapper.env['product.attribute'].search([('name', '=', attribute['name'])]).id
                    attribute_value_ids = []
                    if not attribute_id:
                        attribute_create = mapper.env['product.attribute'].create({'name': attribute['name']})
                        attribute_id = attribute_create.id

                    for attribute_val in attribute['values']:
                        attribute_value_id = ''
                        product_attribute_value_ids = mapper.env['product.attribute.value'].search(
                            [('name', '=', attribute_val)])
                        for product_attribute_value_id in product_attribute_value_ids:
                            if product_attribute_value_id.attribute_id.id == attribute_id:
                                attribute_value_id = product_attribute_value_id.id

                        if not attribute_value_id:
                            # create attribute_value
                            attribute_value_create = mapper.env['product.attribute.value'].create(
                                {'name': attribute_val, 'attribute_id': attribute_id, 'sequence': 1})
                            attribute_value_id = attribute_value_create.id
                        attribute_value_ids.append(attribute_value_id)

                    attributes_value.append(
                        (0, 0, {'attribute_id': attribute_id, 'value_ids': [(6, 0, attribute_value_ids)]}))
            else:
                attributes_value = []

            # product_status
            if result['status'] == 'active':
                status = True
            if result['status'] == 'archived':
                status = False
            if result['status'] == 'draft':
                status = False

            #product_category

            if result['product_type']:
                category_name = result['product_type']

                category = mapper.env['product.category'].search([('name','=',category_name)],limit=1).id
                if not category:
                    values={
                        'name':result['product_type'],
                    }
                    create_category = mapper.env['product.category'].create(values)
                    create_category = create_category.id
                else:
                    create_category = mapper.env['product.category'].search(([('name','=',category_name)]),limit=1).id
            else:
                create_category = None

            vals = {
                'name': result['title'],
                'categ_id': create_category,
                'backend_id': [[6, 0, [bkend_id.id]]],
                'tag_ids': shopify_tag_ids,
                'attribute_line_ids': attributes_value,
                'description': re.sub(re.compile('<.*?>'), '', result['body_html']),
                'active': status,
                'image_medium': img,
                'website_published': result['published_scope'],
                'product_image_ids': images,
            }
            product = mapper.product_id.create(vals)

            #product_variants
            if result['variants']:

                product_templ_mapper = product.backend_mapping.search(
                    [('backend_id', '=', self.backend.id), ('product_id', '=', product.id)], limit=1)

                if product_templ_mapper and product:
                    vals = {
                        'shopify_id': result['id'],
                        'backend_id': self.backend.id,
                        'product_id': product_templ_mapper.product_id.id,
                    }
                    product.backend_mapping.write(vals)
                elif product:
                    vals = {
                        'shopify_id': result['id'],
                        'backend_id': self.backend.id,
                        'product_id': product.id,
                    }
                    product.backend_mapping.create(vals)

                product_templ_mapper_2 = product.backend_mapping.search(
                    [('backend_id', '=', self.backend.id), ('product_id', '=', product.id)], limit=1)

                variant_id_lst = []
                for record in result['variants']:
                    variant_id_lst.append(record['id'])

                for record in variant_id_lst:
                    shopify_api = API(url=self.backend.location, consumer_key=self.backend.consumer_key,
                                consumer_secret=self.backend.consumer_secret, version=self.version, shopify_api=True)

                    record_data = shopify_api.get("variants/{}".format(record)).json()

                    #product_type
                    if record_data['variant']['inventory_management'] == 'shopify':
                        product_type = 'product'
                    elif record_data['variant']['inventory_management'] == 'null':
                        product_type = 'consu'
                    else:
                        product_type= 'product'

                    record_attr_lst = []

                    record_attr_lst.append(record_data['variant']['option1'])
                    record_attr_lst.append(record_data['variant']['option2'])
                    record_attr_lst.append(record_data['variant']['option3'])

                    record_attr_lst_new = []
                    for i in record_attr_lst:
                        if i != None:
                            record_attr_lst_new.append(i)

                    for variant_id in product.product_variant_ids:
                        variant_attr_lst = []

                        for product_template_attribute_value_id in variant_id.product_template_attribute_value_ids:
                            variant_attr_lst.append(product_template_attribute_value_id.name)

                        if variant_attr_lst == record_attr_lst_new:

                            variant_mapper = variant_id.backend_mapping.search(
                                [('backend_id', '=', backend.id), ('product_id', '=', variant_id.id)])

                            if variant_mapper:
                                variant_mapper.write({'product_id': variant_id.id, 'backend_id': backend.id,
                                                      'shopify_id': record_data['variant']['id']})

                                variant_id.shopify_id = record_data['variant']['id']
                                variant_id.default_code = record_data['variant']['sku']
                                variant_id.lst_price = record_data['variant']['price']
                                variant_id.standard_price = record_data['variant']['price']
                                variant_id.weight = record_data['variant']['weight']
                                variant_id.type = product_type
                                variant_id.compare_at_price = record_data['variant']['compare_at_price']

                                if product_type == 'product':
                                    warehouse = mapper.env['stock.warehouse'].search(
                                        [('company_id', '=',
                                          mapper.env['res.company']._company_default_get('product.template').id)],
                                        limit=1
                                    )
                                    if not record_data['variant']['inventory_quantity'] or record_data['variant']['inventory_quantity'] < 0:
                                        record_data['variant']['inventory_quantity'] = 0
                                    else:
                                        record_data['stock_quantity'] = record_data['stock_quantity']
                                        update_stock_id = mapper.env['stock.change.product.qty'].create(
                                        {'product_tmpl_id': variant_id.product_tmpl_id,
                                         'lot_id': False,
                                         'product_id': variant_id.id,
                                         'new_quantity': record_data['variant']['inventory_quantity'],
                                         'location_id': warehouse.lot_stock_id.id,
                                         'product_variant_count': variant_id.product_variant_count})
                                        update_stock_id.change_product_qty()
                                else:
                                    pass
                                break

                            else:
                                variant_mapper.create({'product_id': variant_id.id, 'backend_id': backend.id,
                                                       'shopify_id': record_data['variant']['id']})

                                variant_id.shopify_id = record_data['variant']['id']
                                variant_id.default_code = record_data['variant']['sku']
                                variant_id.lst_price = record_data['variant']['price']
                                variant_id.standard_price = record_data['variant']['price']
                                variant_id.weight = record_data['variant']['weight']
                                variant_id.type = product_type
                                variant_id.compare_at_price = record_data['variant']['compare_at_price']

                                if product_type == 'product':
                                    warehouse = mapper.env['stock.warehouse'].search(
                                        [('company_id', '=',
                                          mapper.env['res.company']._company_default_get('product.template').id)],
                                        limit=1
                                    )
                                    if not record_data['variant']['inventory_quantity'] or record_data['variant'][
                                        'inventory_quantity'] < 0:
                                        record_data['variant']['inventory_quantity'] = 0
                                    else:
                                        record_data['variant']['inventory_quantity'] = record_data['variant']['inventory_quantity']
                                        update_stock_id = mapper.env['stock.change.product.qty'].create(
                                            {'product_tmpl_id': variant_id.product_tmpl_id,
                                             'lot_id': False,
                                             'product_id': variant_id.id,
                                             'new_quantity': record_data['variant']['inventory_quantity'],
                                             'location_id': warehouse.lot_stock_id.id,
                                             'product_variant_count': variant_id.product_variant_count})
                                        update_stock_id.change_product_qty()
                                else:
                                    pass
                                break
                        else:
                            variant_attr_lst.clear()

                    if record_attr_lst_new:
                        record_attr_lst_new.clear()

        return product

    def write_product(self, backend, mapper, res):

        bkend_id = mapper.backend_id.search([('id', '=', backend.id)])

        images = []
        # images
        if res['data']['product']['images']:

            for img in res['data']['product']['images']:
                image = base64.b64encode(requests.get(img['src'].replace('\/', '/')).content)
                name = (img['src'].replace('\/', '/').split('?')[0]).split('/')[-1]

                img_id = mapper.env['product.image'].search([('name', '=', name)]).id

                if not img_id:
                    images.append((0, 0, {'name': name, 'image': image,
                                          'product_tmpl_id': mapper.product_id.id}))
                else:
                    pass

            img = base64.b64encode(requests.get(res['data']['product']['images'][0]['src'].replace('\/', '/')).content)
        else:
            img = ''

        #tags
        if res['data']['product']['tags']:
            shopify_tags = res['data']['product']['tags'].split(',')
            shopify_tag_ids=[]
            for tag in shopify_tags:
                tag_id = mapper.env['product.tags'].search([('name','=',tag)]).id
                if not tag_id:
                    create_tag_id = mapper.env['product.tags'].create({'name': tag})
                    tag_id = create_tag_id.id
                    shopify_tag_ids.append(tag_id)
                else:
                    shopify_tag_ids.append(tag_id)
        else:
            shopify_tag_ids = []

        # attributes
        if res['data']['product']['options']:
            mapper.product_id.attribute_line_ids.unlink()

            attributes_value = []
            for attribute in res['data']['product']['options']:
                attribute_id = mapper.env['product.attribute'].search([('name', '=', attribute['name'])]).id
                attribute_value_ids = []

                if not attribute_id:
                    # create attribute_id
                    attribute_create = mapper.env['product.attribute'].create({'name': attribute['name']})
                    attribute_id = attribute_create.id

                for attribute_val in attribute['values']:
                    attribute_value_id = ''
                    product_attribute_value_ids = mapper.env['product.attribute.value'].search(
                        [('name', '=', attribute_val)])
                    for product_attribute_value_id in product_attribute_value_ids:
                        if product_attribute_value_id.attribute_id.id == attribute_id:
                            attribute_value_id = product_attribute_value_id.id
                            break
                        else:
                            attribute_value_id = False

                    if not attribute_value_id:
                        # create attribute_value
                        attribute_value_create = mapper.env['product.attribute.value'].create(
                            {'name': attribute_val, 'attribute_id': attribute_id, 'sequence': 1})
                        attribute_value_id = attribute_value_create.id
                    attribute_value_ids.append(attribute_value_id)
                attributes_value.append(
                    (0, 0, {'attribute_id': attribute_id, 'value_ids': [(6, 0, attribute_value_ids)]}))
        else:
            attributes_value = []

        #When importing products if product has no variants thn there is a default variant created. But if the product is updated
        #and now it has variants. The earlier one becomes archived as we unlink the default one. But the on hand quantity of the archived one is also counted
        #and that causes issue in the quantity count. To solve this issue I used the below approach. Here I am fetching the product which are archived and making
        #their quantity 0.

        # for i in mapper.env['product.product'].search([('active','=',False),('combination_indices','=',''),('product_tmpl_id','=',mapper.product_id.id)]):
        # for i in mapper.env['product.product'].search([('product_tmpl_id','=',mapper.product_id.id)]):
        for i in mapper.env['product.product'].search([('active', '=', False)]):
            # if i.product_tmpl_id == mapper.product_id:
            # warehouse = mapper.env['stock.warehouse'].search(
            #             [('company_id', '=', mapper.env.company.id)], limit=1
            #         )
            # stock_quant = mapper.env['stock.quant']
            # stock_quant.with_context(inventory_mode=True).create({
            #     'product_id': i.id,
            #     'location_id': warehouse.lot_stock_id.id,
            #     'inventory_quantity': 0,
            # })
            warehouse = mapper.env['stock.warehouse'].search(
                [('company_id', '=',
                  mapper.env['res.company']._company_default_get('product.template').id)],
                limit=1
            )
            update_stock_id = mapper.env['stock.change.product.qty'].create(
                {'product_tmpl_id': i.product_tmpl_id,
                 'lot_id': False,
                 'product_id': i.id,
                 'new_quantity': 0,
                 'location_id': warehouse.lot_stock_id.id,
                 'product_variant_count': i.product_variant_count})
            update_stock_id.change_product_qty()

        #product_status
        if res['data']['product']['status'] == 'active':
            status= True
        if res['data']['product']['status'] == 'archived':
            status= False
        if res['data']['product']['status'] == 'draft':
            status= False

        #product_category
        if res['data']['product']['product_type']:
            category_name = res['data']['product']['product_type']

            category = mapper.env['product.category'].search([('name','=',category_name)],limit=1).id
            if not category:
                values={
                    'name':res['data']['product']['product_type'],
                }
                create_category = mapper.env['product.category'].create(values)
            else:
                create_category = mapper.env['product.category'].search(([('name','=',category_name)]),limit=1).id
        else:
            create_category = None

        vals = {
            'name': res['data']['product']['title'],
            'categ_id': create_category,
            'attribute_line_ids': attributes_value,
            'backend_id': [[6, 0, [bkend_id.id]]],
            'tag_ids': shopify_tag_ids,
            'description': re.sub(re.compile('<.*?>'), '', res['data']['product']['body_html']),
            'active': status,
            'image_medium':img,
            'website_published': res['data']['product']['published_scope'],
            'product_image_ids': images,
        }

        mapper.product_id.write(vals)

        #product_variants
        if res['data']['product']['variants']:

            variant_id_lst = []
            for record in res['data']['product']['variants']:
                variant_id_lst.append(record['id'])

            for record in variant_id_lst:
                shopify_api = API(url=self.backend.location, consumer_key=self.backend.consumer_key,
                            consumer_secret=self.backend.consumer_secret, version=self.version, shopify_api=True)

                record_data = shopify_api.get("variants/{}".format(record)).json()

                #product_type
                if record_data['variant']['inventory_management'] == 'shopify':
                    product_type = 'product'
                elif record_data['variant']['inventory_management'] == 'null':
                    product_type = 'consu'
                else:
                    product_type = 'product'

                record_attr_lst = []
                record_attr_lst.append(record_data['variant']['option1'])
                record_attr_lst.append(record_data['variant']['option2'])
                record_attr_lst.append(record_data['variant']['option3'])

                record_attr_lst_new = []
                for i in record_attr_lst:
                    if i != None:
                        record_attr_lst_new.append(i)


                for variant_id in mapper.product_id.product_variant_ids:
                    variant_attr_lst = []

                    for product_template_attribute_value_id in variant_id.product_template_attribute_value_ids:
                        variant_attr_lst.append(product_template_attribute_value_id.name)

                    if variant_attr_lst == record_attr_lst_new:
                        variant_mapper = variant_id.backend_mapping.search(
                            [('backend_id', '=', backend.id), ('product_id', '=', variant_id.id)])

                        if variant_mapper:
                            variant_mapper.write({'product_id': variant_id.id, 'backend_id': backend.id,
                                                  'shopify_id': record_data['variant']['id']})

                            variant_id.shopify_id = record_data['variant']['id']
                            variant_id.default_code = record_data['variant']['sku']
                            variant_id.lst_price = record_data['variant']['price']
                            variant_id.standard_price = record_data['variant']['price']
                            variant_id.weight = record_data['variant']['weight']
                            variant_id.type = product_type
                            variant_id.compare_at_price= record_data['variant']['compare_at_price']

                            if product_type == 'product':
                                warehouse = mapper.env['stock.warehouse'].search(
                                    [('company_id', '=',
                                      mapper.env['res.company']._company_default_get('product.template').id)],
                                    limit=1
                                )
                                if not record_data['variant']['inventory_quantity'] or record_data['variant'][
                                    'inventory_quantity'] < 0:
                                    record_data['variant']['inventory_quantity'] = 0
                                else:
                                    record_data['variant']['inventory_quantity'] = record_data['variant']['inventory_quantity']
                                    update_stock_id = mapper.env['stock.change.product.qty'].create(
                                        {'product_tmpl_id': variant_id.product_tmpl_id,
                                         'lot_id': False,
                                         'product_id': variant_id.id,
                                         'new_quantity': record_data['variant']['inventory_quantity'],
                                         'location_id': warehouse.lot_stock_id.id,
                                         'product_variant_count': variant_id.product_variant_count})
                                    update_stock_id.change_product_qty()
                            break
                        else:
                            variant_mapper.create({'product_id': variant_id.id, 'backend_id': backend.id,
                                                   'shopify_id': record_data['variant']['id']})

                            variant_id.shopify_id = record_data['variant']['id']
                            variant_id.default_code = record_data['variant']['sku']
                            variant_id.lst_price = record_data['variant']['price']
                            variant_id.standard_price = record_data['variant']['price']
                            variant_id.weight = record_data['variant']['weight']
                            variant_id.type = product_type
                            variant_id.compare_at_price = record_data['variant']['compare_at_price']

                            if product_type == 'product':
                                warehouse = mapper.env['stock.warehouse'].search(
                                    [('company_id', '=',
                                      mapper.env['res.company']._company_default_get('product.template').id)],
                                    limit=1
                                )
                                if not record_data['variant']['inventory_quantity'] or record_data['variant'][
                                    'inventory_quantity'] < 0:
                                    record_data['variant']['inventory_quantity'] = 0
                                else:
                                    record_data['variant']['inventory_quantity'] = record_data['variant']['inventory_quantity']
                                    update_stock_id = mapper.env['stock.change.product.qty'].create(
                                        {'product_tmpl_id': variant_id.product_tmpl_id,
                                         'lot_id': False,
                                         'product_id': variant_id.id,
                                         'new_quantity': record_data['variant']['inventory_quantity'],
                                         'location_id': warehouse.lot_stock_id.id,
                                         'product_variant_count': variant_id.product_variant_count})
                                    update_stock_id.change_product_qty()
                            break
                    else:
                        variant_attr_lst.clear()

                if record_attr_lst_new:
                    record_attr_lst_new.clear()