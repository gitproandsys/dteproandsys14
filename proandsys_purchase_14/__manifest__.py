# -*- coding: utf-8 -*-

{
    'name': 'Proandsys Compras',
    'version': '14.0.0.1',
    'category': 'Purchase',
    'license': 'AGPL-3',
    'summary': 'Localizacion de Compras chile',
    'author': 'proandsys',
    'website': 'http://www.odooconsultores.cl',
    'depends': ['purchase', 'stock_landed_costs', 'account'],
    'data': [
        'views/maintainers_view.xml',
        'views/product_view.xml',
        'views/stock_view.xml',
        'views/purchase_order_view.xml',
        'views/landed_cost_view.xml',
        'views/din_view.xml',
        'views/account_move_view.xml',
        'reports/summary_landed_cost.xml',
        'reports/orden_compra.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
}
