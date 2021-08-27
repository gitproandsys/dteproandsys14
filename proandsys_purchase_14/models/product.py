
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    landed_cost_ok = fields.Boolean('Landed Cost', default=False)

