# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import AccessError, UserError, ValidationError

import logging
logger = logging.getLogger(__name__)


class SaleOrderPs(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _get_default_contacts(self):
        self.contacto_invoice_id = False
        self.contacto_collection_id = False
        if self.partner_id.contacto_invoice_id:
            self.contacto_invoice_id = self.partner_id.contacto_invoice_id.id
        else:
            self.contacto_invoice_id = self.partner_id.id
        if self.partner_id.contacto_collection_id:
            self.contacto_collection_id = self.partner_id.contacto_collection_id.id
        else:
            self.contacto_collection_id = self.partner_id.id

    @api.constrains('contacto_invoice_id', 'contacto_collection_id')
    def _check_contact(self):
        if self.contacto_invoice_id:
            if self.contacto_invoice_id.parent_id:
                if self.contacto_invoice_id.parent_id.id != self.partner_id.id:
                    raise exceptions.Warning('El contacto de facturación no pertenece a este cliente')
            else:
                if self.contacto_invoice_id.id != self.partner_id.id:
                    raise exceptions.Warning('El contacto de facturación no pertenece a este cliente')
        if self.contacto_collection_id:
            if self.contacto_collection_id.parent_id:
                if self.contacto_collection_id.parent_id.id != self.partner_id.id:
                    raise exceptions.Warning('El contacto de cobranza no pertenece a este cliente')
            else:
                if self.contacto_collection_id.id != self.partner_id.id:
                    raise exceptions.Warning('El contacto de cobranza no pertenece a este cliente')

    @api.constrains('max_item_invoice')
    def _check_max_item_invoice(self):
        if self.l10n_latam_document_type_id.code in ['33', '34', '56', '61']:
            if self.max_item_invoice > 60:
                raise Warning('El valor maximo por factura es de 60 Items')
        else:
            if self.max_item_invoice > 1000:
                raise Warning('El valor maximo por factura es de 1000 Items')

    def default_type_document(self):
        if self.env.user.company_id.sii_doc_type_id:
            doc = self.env.user.company_id.sii_doc_type_id.id
            return doc

    @api.onchange('l10n_latam_document_type_id')
    def change_max_item(self):
        if self.l10n_latam_document_type_id.code in ['33', '34', '56', '61']:
            self.update({
                'max_item_invoice': 60,
            })
        else:
            self.update({
                'max_item_invoice': 1000,
            })

    @api.onchange('order_line')
    def qty_item_pedido(self):
        self.update({
            'qty_item': len(self.order_line),
        })

    contacto_invoice_id = fields.Many2one('res.partner','Contacto de Facturación', domain="['&',('parent_id','child_of', partner_id),('type','=', 'contact')]")
    contacto_collection_id = fields.Many2one('res.partner', 'Contacto de Cobranza',
                                 domain="['&',('parent_id','child_of', partner_id),('type','=', 'contact')]")

    max_item_invoice = fields.Integer('Cantidad de Items por factura', default=60, required=True)
    qty_item = fields.Integer('Cantidad de Items del Pedido')
    reference_lines = fields.One2many('l10n_cl_dte.reference', 'sale_id', string='Lineas de Referencias', copy=False)

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Tipo de documento', required=True,
                                      domain=[('internal_type', '=', 'invoice')], default=default_type_document)

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
            self.company_id.name, self.company_id.id))
    
        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'invoice_user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(
                self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'contacto_invoice_id': self.contacto_invoice_id.id,
            'contacto_collection_id': self.contacto_collection_id.id,
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'reference_lines': [(6, 0, self.reference_lines.ids)],
        }
        return invoice_vals

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    
        for line in self.order_line:
            if len(invoiceable_line_ids) < self.max_item_invoice:
                if line.display_type == 'line_section':
                    # Only invoice the section if one of its lines is invoiceable
                    pending_section = line
                    continue
                if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
                    if line.is_downpayment:
                        # Keep down payment lines separately, to put them together
                        # at the end of the invoice, in a specific dedicated section.
                        down_payment_line_ids.append(line.id)
                        continue
                    if pending_section:
                        invoiceable_line_ids.append(pending_section.id)
                        pending_section = None
                    invoiceable_line_ids.append(line.id)
    
        return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)
