# Used to define module metadata, dependencies and asset loading
{
    'name': ' Woodforest Payment',
    'version': '17.0.1.0.0',
    'depends': ['point_of_sale', 'payment', 'account'],
    'author': 'Jorge',
    'category': 'Point of Sale',
    'license': 'LGPL-3',
    'summary': 'Woodforest Payment Integration',
    'description': 'This module allows integration of a physical payment terminal via Payrillium with Odoo POS.',
    'post_init_hook': 'show_payrillium_wizard_once',
    'data': [
        'views/payrillium_wizard_views.xml',
        'security/ir.model.access.csv',
        'views/pos_payment_method_views.xml',
        "data/data.xml",
        'views/res_config_settings.xml',
        'views/payrillium_terminal_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'pos_payrillium/static/src/js/show_config_wizard.js',
        ],
        'point_of_sale._assets_pos': [
            'pos_payrillium/static/src/js/config_loader.js',
            'pos_payrillium/static/src/js/api_service.js',
            'pos_payrillium/static/src/js/payment_screen.js',
            'pos_payrillium/static/src/js/product_screen.js',
            'pos_payrillium/static/src/js/ticket_screen.js',
            'pos_payrillium/static/src/js/order_models.js',
        #      (
        #     'after',
        #     'point_of_sale/static/src/app/store/models.js',
        #     'pos_payrillium/static/src/js/extend_models.js'
        # ),
        ('after', 'point_of_sale/static/src/app/store/pos_store.js', 'pos_payrillium/static/src/js/extend_models.js'),
        ],
    },
    'icon': '/pos_payrillium/static/description/icon.png',
    'installable': True,
    'application': True,
    'auto_install': False,
}
