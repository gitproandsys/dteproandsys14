# -*- encoding: utf-8 -*-
##############################################################################

{
    "name": "Reportes Tributarios Chile",
    "version": "14.0",
    "description": "",
    "author": "",
    "website": "",   
    "data":[
        "views/wizard.xml",
        'views/account.xml',
        'views/report_trial_balance.xml',
        "reports/formato_papel.xml",
        "reports/fact_abierta.xml", 
        "reports/libro_venta.xml",
        "reports/libro_compra.xml",
        "reports/libro_guias.xml", 
        "reports/libro_honorarios.xml",
        "reports/libro_diario.xml",
        "reports/balance_tributario.xml",        
        ], 
    "depends": ['base', 'proandsys_dte_14', 'report_xlsx','account_financial_report', 'proandsys_purchase_14'],
    "active": False,
    "installable": True,
    "auto_install": False,
    "certificate" : "",
    "images": [
                        ],
}

