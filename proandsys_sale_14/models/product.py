# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from odoo.tools import float_is_zero, float_compare

import logging
logger = logging.getLogger(__name__)


class ProductTemplatePs(models.Model):
    _inherit = 'product.template'

    is_embroidery = fields.Boolean(string='Es un bordado')