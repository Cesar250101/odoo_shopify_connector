# -*- coding: utf-8 -*-
{
    'name': "Odoo Shopify Connector",

    'summary': """
     This Module will Connect Odoo with Shopify and synchronise Data.
       """,

    'description': """
        This Module will Connect Odoo with Shopify and synchronise Data.
    """,
    'author': "Techspawn Solutions Pvt. Ltd.",
    'website': "http://www.techspawn.com",
    'license':'OPL-1',
    'category': 'custom',
    'version': '12.0.0',
    'depends': ['base',
		        'product',
                'website',
                'stock',
                'sale',
                'sale_management',
                'website_sale',],
    'price': 29.00,
    'currency': 'USD',
    'data': [
        'security/bridge_security.xml',
        'security/ir.model.access.csv',
        'views/sp_bridge_view.xml',
        'views/product.xml',
        'views/customer.xml',
        'views/message_wizard.xml',
        'views/sale.xml',
        'views/product_tag.xml',
        'views/cron.xml',
        'wizard/selective_export.xml',
        'wizard/multiple_product_export.xml',
        'wizard/multiple_customer_export.xml',
    ],
    'images': ['images/shopify_v12.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
}
