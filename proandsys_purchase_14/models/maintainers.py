# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Regime(models.Model):
    _name = 'regime'
    _description = 'Regime'

    name = fields.Char('Name')

class TransportRoute(models.Model):
    _name = 'transport.route'
    _description = 'Ruta de transporte'

    name = fields.Char('Name')

class Container(models.Model):
    _name = 'container'
    _description = 'Contenedor'

    name = fields.Char('Name')

class Tracking(models.Model):
    _name = 'tracking'
    _description = 'tracking'

    Name = fields.Char('Name')

class TrackingOc(models.Model):
    _name = 'tracking.oc'
    _description = 'OC tracking'

    name = fields.Char('Name')
    fecha = fields.Date('Date')
    oc_related = fields.Many2one('purchase.order', 'Purchase order', ondelete='cascade')

class ContainerOC(models.Model):
    _name = 'container.oc'
    _description = 'container'

    container = fields.Many2one('container', 'Container')
    serial = fields.Char('Serial')
    purchase_id = fields.Many2one('purchase.order', 'Purchase order', ondelete='cascade')
    sequence = fields.Integer('Sequence', default=9999,
                help="Shows the sequence of this line in the invoice.")
    # shows sequence on the invoice line
    sequence2 = fields.Integer('Sequence 2', realted='sequence', readonly=True, store=True,
                                        help="Shows the sequence of this line in the invoice.")
    arrival_date = fields.Date('Arrival date')
    reception_date = fields.Date('Reception date')
    return_date = fields.Date('Return date')
    demurrage_amount = fields.Float('Demurrage Amount')
    notes = fields.Char('Notes')

class IncomexFolder(models.Model):
    _name = 'incomex.folder'
    _description = 'incomex'

    name = fields.Char('Reference')
    date = fields.Date('Incomex date')
    total_cost = fields.Float('Total incomex cost')

