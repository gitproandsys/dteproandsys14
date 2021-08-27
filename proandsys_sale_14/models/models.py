# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import logging
_logger = logging.getLogger(__name__)


class ReferenciasDte(models.Model):
    _name = 'l10n_cl_dte.reference'
    _description = 'Mantenedor de Referencias'

    def _get_type(self):
        inv_type = self._context.get('move_type', None)
        return inv_type

    invoice_id = fields.Many2one('account.move', 'Inovice')
    tpo_doc_ref = fields.Many2one('l10n_latam.document.type', 'Tipo de Documento Referente', required=True)
    ref_folio = fields.Char('Folio de referencia', size=18, required=True)
    ref_date = fields.Date('Fecha de referencia', required=True)
    ref_reason = fields.Selection([('1', 'Anular documento'), ('2', 'Arregla el texto'), ('3', 'Cantidad de Arreglos')],
                                  'Causa')
    type = fields.Char('Tipo de factura', default=_get_type)
    external_document = fields.Boolean('Documento externo', required=False)
    picking_id = fields.Many2one('stock.picking', 'Picking')
    sale_id = fields.Many2one('sale.order', 'Sale')

