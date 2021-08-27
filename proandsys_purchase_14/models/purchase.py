# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    policy_reference = fields.Char('Policy reference')
    shipper = fields.Char('Shipper')
    consignee = fields.Char('Consignee')
    landed_cost_id = fields.Many2one('stock.landed.cost', 'Landed Cost', states=READONLY_STATES)
    acquisition_country_id = fields.Many2one('res.country', 'Acquisicion country', states=READONLY_STATES)
    origin_country_id = fields.Many2one('res.country', 'Origin country', states=READONLY_STATES)
    regime_id = fields.Many2one('regime', 'Regime', states=READONLY_STATES)
    transport_id = fields.Many2one('res.partner', 'Transport', states=READONLY_STATES)
    transport_route_id = fields.Many2one('transport.route', 'Transport route', states=READONLY_STATES)
    shipment_port_id = fields.Many2one('res.country.state', 'Port of shipment', states=READONLY_STATES)
    destination_port_id = fields.Many2one('res.country.state', 'Destination port', states=READONLY_STATES)
    tracking = fields.Many2one('tracking', 'Purchase order tracking')
    folder_id = fields.Many2one('incomex.folder', 'Incomex folder')
    tracking_oc_ids = fields.One2many('tracking.oc', 'oc_related', 'Purchase order planning')
    container_ids = fields.One2many('container.oc', 'purchase_id', 'Containers')
    order_type = fields.Selection(([('imported','Imported'),('national', 'National')]),
                            'Purchase order type', default='national', states=READONLY_STATES)
    product_type = fields.Selection([('materials', 'Materials'),('services', 'Services')],
                                      'Product type', default='materials', states=READONLY_STATES)
    max_line_sequence = fields.Integer('Max sequence in lines', compute='_compute_max_line_sequence', store=True)
    validate_uid =fields.Many2one('res.users','Validado Por')

    def button_confirm(self):
        for record in self:
            record.validate_uid = self.env.user
            return super(PurchaseOrder, record).button_confirm()
        

    @api.depends('container_ids')
    def _compute_max_line_sequence(self):
        """Allow to know the highest sequence entered in invoice lines.
        Then we add 1 to this value for the next sequence.
        This value is given to the context of the o2m field in the view.
        So when we create new invoice lines, the sequence is automatically
        added as :  max_sequence + 1
        """
        for container in self:
            container.max_line_sequence = (max(container.mapped('container_ids.sequence') or [0]) + 1)

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.container_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def write(self, values):
        res = super(PurchaseOrder, self).write(values)
        self._reset_sequence()
        return res

    @api.onchange('order_type')
    def onchange_order_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get(
            'company_id') or self.env.user.company_id.id
        if self.order_type == 'imported':
            nombre = 'Recepciones Importacion'
        else:
            nombre = 'Recepcion Nacional'
        types = type_obj.search(
            [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id), ('name', '=', nombre)])
        if types:
            self.update({'picking_type_id': types[0].id})

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    barcode = fields.Char('Codigo', related='product_id.barcode')

class PurchaseCarpetaImportacion(models.Model):
    _inherit = 'incomex.folder'

    purchase_order_ids = fields.One2many('purchase.order', 'folder_id', 'Purchase Order')

