# -*- coding: utf-8 -*-

{
	'name': 'Proandsys - Ventas Chile',
	'version': '1',
	'author': '[Proandsys]',
	'website': 'http://www.odooconsultores.cl',
	'license': 'AGPL-3',
	'category': 'Localization',
	'summary': 'Localizacion Chilena de Ventas',
	'description': 
"""
   -Agrega division y Contacto al pedido de Venta.     

""",
	'depends': ['sale','proandsys_partner_14', 'purchase', 'sale_management'],
	'data': [
		'views/sale_view.xml',
	],
	'installable': True,	
}
