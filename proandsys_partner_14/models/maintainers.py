# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class EconomicActivity(models.Model):
	_name = 'economic.activity'	

	name = fields.Char('Actividad Económica', required=True)
	code = fields.Char('Código', required=True)