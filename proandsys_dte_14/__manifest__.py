# -*- coding: utf-8 -*-

{
	'name': 'Proandsys - DTE Chile',
	'version': '0.0.1',
	'author': '[Proandsys]',
	'website': '[http://www.odooconsultores.cl]',
	'category': 'Accounting & Finance',
	'summary': 'Localizacion Chilena Para Facturacion Electronica',
	'description':
"""
    Modulo de facturacion electronica y firmador digital de los mismos.

    Se debe instalar los siguientes paquetes como dependencia:
        - python-cjson
        - python-unittest2
        - python-requests

""",
	'depends': [
		'base',
		'account',
		'proandsys_partner_14',
		'proandsys_sale_14',
		'sale_stock',
		'sale',
		'web',
		'stock_account',
        'l10n_latam_invoice_document',
	],	
	'data': [
		'security/ir.model.access.csv',
        'data/codigo_traslado.xml',
        'data/forma_pago.xml',
        'data/tipo_traslado.xml',
        'data/ind_servicio.xml',
        'data/payment_type.xml',
        'data/tipo_imp_guia.xml',
        'data/tipo_despacho.xml',
        'data/cron.xml',
        'wizard/import_xml_timbre_view.xml',
        'wizard/cesion_facturas_view.xml',
        'wizard/send_ack_view.xml',
		'views/views.xml',
		'views/account_tax.xml',
        'views/res_config_view.xml',
		'views/account_move.xml',
	],

}

