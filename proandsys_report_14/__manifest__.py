# -*- coding: utf-8 -*-

{
	'name': 'Proandsys - Reportes DTE',
	'version': '0.0.1',
	'author': '[Proandsys]',
	'website': '[http://www.odooconsultores.cl]',
	'category': 'Stock',
	'summary': 'Localizacion Chilena el ajuste de reportes',
	'description':
"""
    Ajuste de reporte de facturas
    Ajuste de reporte de guias
    Ajuste de reporte de presupuestos y pedidos

""",
	'depends': [
		'base',
        'account',
		'proandsys_partner_14',
		'proandsys_sale_14',
		'proandsys_dte_14',
		'proandsys_stock_14',

	],	
	'data': [
		'report/account_move.xml',
		'report/stock_picking.xml',
	],

}

