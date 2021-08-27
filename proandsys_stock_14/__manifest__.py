# -*- coding: utf-8 -*-

{
	'name': 'Proandsys - Stock DTE Chile',
	'version': '0.0.1',
	'author': '[Proandsys]',
	'website': '[http://www.odooconsultores.cl]',
	'category': 'Stock',
	'summary': 'Localizacion Chilena Para Stock',
	'description':
"""
    Modulo de stock.

""",
	'depends': [
		'base',
		'proandsys_partner_14',
		'proandsys_sale_14',
		'stock',
		'proandsys_dte_14',
        'l10n_latam_invoice_document',
	],	
	'data': [
        'data/l10n_latam_document_type_id.xml',
		'views/stock_picking.xml',
	],

}

