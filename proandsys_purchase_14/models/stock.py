
from odoo import fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    reception_document = fields.Selection([('dispatch_order','Dispatch Order'),('invoice','Invoice')], 'Reception document')
    document_number = fields.Char('Document number')

