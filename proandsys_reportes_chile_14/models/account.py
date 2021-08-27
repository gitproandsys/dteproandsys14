from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    mostrar_v = fields.Boolean('Mostrar en libro de venta')  
    mostrar_c = fields.Boolean('Mostrar en libro de compra')

class account_account_type(models.Model):
    _inherit = 'account.account.type'

    report_type = fields.Selection(string='Categoria de Cuenta', store=True,
            selection= [('income', 'Ingresos'),
                        ('expense','Egresos'),
                        ('asset','Activos'),
                        ('liability','Pasivos')])
