import logging
from ..model.api import API
from datetime import datetime
from datetime import timedelta
from ..unit.backend_adapter import ShopifyImportExport

_logger = logging.getLogger(__name__)

class ShopifySaleOrderImport(ShopifyImportExport):

    def get_api_method(self, method, args, count=None, date=None):

        api_method = None
        if not args[0]:
            # api_method = 'orders.json?financial_status=pending&limit=2&page=' + str(count)
            api_method = 'orders.json?status=any'
        else:
            api_method = 'orders.json?ids=' + str(args[0]['id'])
        return api_method

    def import_sales_order(self, method, arguments, count=None, date=None):

        _logger.debug("Start calling Shopify api %s", method)
        result = {}

        res = self.importer(method, arguments, count, date)
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

    def create_sale_order(self, backend, mapper, res, status=True):

        try:
            partner_id = mapper.env['shopify.odoo.res.partner'].search(
                    [('backend_id', '=', backend.id), ('shopify_id', '=', res['data']['orders'][0]['customer']['id'])])
        except:
            partner_id = False

        record = res['data']

        if record['orders'] != []:
            product_ids = []
            if record['orders'][0]['created_at']:
                date_created = record['orders'][0]['created_at']
            else:
                date_created = ''

            if partner_id:
                values = {
                    'partner_id': partner_id[0].customer_id.id,
                    'create_date': date_created.split('T')[0],
                    'confirmation_date': date_created.split('T')[0],
                }

                sale_order = mapper.env['sale.order'].create(values)

                sale_order.shopify_payment_status = record['orders'][0]['financial_status']
                sale_order.shopify_sale_order_number = record['orders'][0]['name']
                for i in record['orders'][0]['payment_gateway_names']:
                    sale_order.shopify_payment_method = str(i)

                if record['orders'][0]['financial_status'] == "pending":
                    status = 'draft'
                elif record['orders'][0]['financial_status'] == "paid":
                    status = 'sale'
                elif record['orders'][0]['financial_status'] == "voided":
                    status = 'cancel'
                else:
                    status = 'draft'

                sale_order.state = status

                if 'line_items' in res['data']['orders'][0]:
                    product_ids = []
                    for lines in record['orders'][0]['line_items']:
                        if 'product_id' in lines:
                            product_template_id = mapper.env['shopify.odoo.product.template'].search(
                                [('backend_id', '=', backend.id),
                                 ('shopify_id', '=', lines['product_id'])])

                            if product_template_id:
                                pass
                            else:
                                if lines['product_id'] == False:
                                    break
                                else:
                                    product = mapper.env['product.template']
                                    product.single_importer(backend, lines['product_id'], False)
                                    product_template_id = mapper.env['shopify.odoo.product.template'].search(
                                        [('backend_id', '=', backend.id), ('shopify_id', '=', lines['product_id'])])

                            product = product_template_id.product_id.product_variant_id

                            product_variant_id = mapper.env['shopify.odoo.product.product'].search(
                                [('backend_id', '=', backend.id),
                                 ('shopify_id', '=', lines['variant_id'])])
                            product = product_variant_id.product_id

                            tax_ids = []
                            if lines['tax_lines']:
                                for tax in lines['tax_lines']:
                                    if tax['title']:
                                        tax_id = mapper.env['account.tax'].search([('name', '=', tax['title'])])
                                        if not tax_id:
                                            tax_rate = tax['rate'] * 100
                                            vals = {
                                                'name': tax['title'],
                                                'amount': float(tax_rate),
                                            }
                                            tax_create_id = mapper.env['account.tax'].create(vals)
                                            tax_ids.append(tax_create_id.id)
                                        else:
                                            tax_ids.append(tax_id.id)
                            for prod in product:
                                result = [0, 0, {
                                    'product_id': prod.id,
                                    'price_unit': lines['price'],
                                    'product_uom_qty': lines['quantity'],
                                    'product_uom': 1,
                                    'price_subtotal': record['orders'][0]['subtotal_price'],
                                    'name': lines['name'].replace('\\/', ''),
                                    'order_id': sale_order.id,
                                    'backend': str(lines['id']),
                                    'tax_id': [(6, 0, tax_ids)],
                                }]

                                product_ids.append(result)
                    sale_order.update({'order_line': product_ids,'backend_id':backend})
            return sale_order

    def write_sale_order(self, backend, mapper, res):
        try:
            partner_id = mapper.env['shopify.odoo.res.partner'].search(
                [('backend_id', '=', backend.id), ('shopify_id', '=', res['data']['orders'][0]['customer']['id'])])
        except:
            partner_id = False

        record = res['data']

        sale_order_id = mapper.order_id
        if record['orders']:
            sale_order_id.shopify_payment_status = record['orders'][0]['financial_status']
            sale_order_id.shopify_sale_order_number = record['orders'][0]['name']
            for i in record['orders'][0]['payment_gateway_names']:
                sale_order_id.shopify_payment_method = str(i)

            if record['orders'][0]['financial_status'] == "pending":
                status = 'draft'
            elif record['orders'][0]['financial_status'] == "paid":
                status = 'sale'
            elif record['orders'][0]['financial_status'] == "voided":
                status = 'cancel'
            else:
                status = 'draft'

        else:
            sale_order_id.shopify_payment_status = ''
            sale_order_id.shopify_sale_order_number = ''
            sale_order_id.shopify_payment_method = ''
            status = 'draft'

        sale_order_id.state = status
        if record['orders']:
            if 'line_items' in res['data']['orders'][0]:
                product_ids = []
                for lines in record['orders'][0]['line_items']:
                    if 'product_id' in lines:
                        product_template_id = mapper.env['shopify.odoo.product.template'].search(
                            [('backend_id', '=', backend.id),
                            ('shopify_id', '=', lines['product_id'])])
                        if product_template_id:
                            pass
                        else:
                            if lines['product_id'] == False:
                                break
                            else:
                                product = mapper.env['product.template']
                                product.single_importer(backend, lines['product_id'], False)
                                product_template_id = mapper.env['shopify.odoo.product.template'].search(
                                    [('backend_id', '=', backend.id), ('shopify_id', '=', lines['product_id'])])

                        # product = product_template_id.product_id.product_variant_id
                        product = []
                        # for i in product_template_id.product_id.product_variant_ids:

                        # sale_order_line was not taking proper product variants as the response have two separate id one
                        # for product and other for variant so the below code.

                        product_variant_id = mapper.env['shopify.odoo.product.product'].search(
                            [('backend_id', '=', backend.id),
                            ('shopify_id', '=', lines['variant_id'])])
                        product = product_variant_id.product_id

                        tax_ids = []
                        if lines['tax_lines']:
                            for tax in lines['tax_lines']:
                                if tax['title']:
                                    tax_id = mapper.env['account.tax'].search([('name', '=', tax['title'])])
                                    if not tax_id:
                                        tax_rate = tax['rate'] * 100
                                        vals = {
                                            'name': tax['title'],
                                            'amount': float(tax_rate),
                                            'amount_type': 'percent',
                                        }
                                        tax_create_id = mapper.env['account.tax'].create(vals)
                                        tax_ids.append(tax_create_id.id)
                                    else:
                                        tax_ids.append(tax_id.id)

                        for prod in product:
                            result = {'product_id': prod.id,
                                    'price_unit': lines['price'],
                                    'product_uom_qty': lines['quantity'],
                                    'product_uom': 1,
                                    'price_subtotal': record['orders'][0]['subtotal_price'],
                                    'name': lines['name'].replace('\\/', ''),
                                    'order_id': sale_order_id.id,
                                    'backend': str(lines['id']),
                                    'tax_id': [(6, 0, tax_ids)],
                                    }
                            product_ids.append(result)

                for details in product_ids:
                    order = mapper.env['sale.order.line'].search(
                        [('backend', '=', details['backend'])])
                    if order:
                        order.write(details)
                    else:
                        order.create(details)