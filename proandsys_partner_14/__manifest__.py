# -*- coding: utf-8 -*-

{
	'name': 'Proandsys - Partner Chile',
	'version': '0.0.1',
	'author': '[Proandsys]',
	'website': 'http://www.odooconsultores.cl',
	'license': 'AGPL-3',
	'category': 'Localization',
	'summary': 'Localizacion Chilena del Partner',
	'description': 
"""
   -Agrega giro.
   -Restringe el campo rut que sea único por partner.
   -Agrega mantenedor de actividades economicas previamente cargadas.

""",
	'depends': ['base', 'account'],
	'data': [
        'security/l10n_cl_dte_security.xml',
        'security/ir.model.access.csv',
        'wizard/set_company_view.xml',
        'views/menu_root.xml',
		'views/maintainers_view.xml',
		'views/company_view.xml',
		'views/partner_view.xml',
		'data/eco_act_data.xml',
	],
	'installable': True,	
}
