# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
import logging
logger = logging.getLogger(__name__)


class ResConfigSettingsDte(models.TransientModel):
    _inherit = 'res.config.settings'

    email_folios = fields.Boolean(string="Correo finalización de folios", default=False)
    qty_folios = fields.Integer(string="Cant. de Folios", default=20)
    email_validate = fields.Boolean(string="Correo de validación", default=False)
    email_to_due = fields.Boolean(string="Correo de pronto vencimiento", default=False)
    email_due_today = fields.Boolean(string="Correo del dia de vencimiento", default=False)
    email_due_before = fields.Boolean(string="Correo de vencida", default=False)
    qty_days = fields.Integer(string="Cant. de dias antes", default=3)

    email_to_due_supplier = fields.Boolean(string="Correo de Pronto Vencimiento de Facturas de Proveedor", default=False)
    email_due_today_supplier = fields.Boolean(string="Correo del Dia de Vencimiento de Factura de Proveedor", default=False)
    email_due_before_supplier = fields.Boolean(string="Correo de Facturas de Proveedor Vencidas", default=False)
    qty_days_supplier = fields.Integer(string="Cant. de dias antes", default=3)

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsDte, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            email_folios=params.get_param('email_folios'),
            qty_folios=int(params.get_param('qty_folios')),
            email_validate=params.get_param('email_validate'),
            email_to_due=params.get_param('email_to_due'),
            email_due_today=params.get_param('email_due_today'),
            email_due_before = params.get_param('email_due_before'),
            qty_days=int(params.get_param('qty_days')),
    
            email_to_due_supplier=params.get_param('email_to_due_supplier'),
            email_due_today_supplier=params.get_param('email_due_today_supplier'),
            email_due_before_supplier=params.get_param('email_due_before_supplier'),
            qty_days_supplier=int(params.get_param('qty_days_supplier')),
        )
        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('email_folios', self.email_folios)
        self.env['ir.config_parameter'].sudo().set_param('qty_folios', self.qty_folios)
        self.env['ir.config_parameter'].sudo().set_param('email_validate', self.email_validate)
        self.env['ir.config_parameter'].sudo().set_param('email_to_due', self.email_to_due)
        self.env['ir.config_parameter'].sudo().set_param('email_due_today', self.email_due_today)
        self.env['ir.config_parameter'].sudo().set_param('email_due_before', self.email_due_before)
        self.env['ir.config_parameter'].sudo().set_param('qty_days', self.qty_days)

        self.env['ir.config_parameter'].sudo().set_param('email_to_due_supplier', self.email_to_due_supplier)
        self.env['ir.config_parameter'].sudo().set_param('email_due_today_supplier', self.email_due_today_supplier)
        self.env['ir.config_parameter'].sudo().set_param('email_due_before_supplier', self.email_due_before_supplier)
        self.env['ir.config_parameter'].sudo().set_param('qty_days_supplier', self.qty_days_supplier)
        super(ResConfigSettingsDte, self).set_values()
