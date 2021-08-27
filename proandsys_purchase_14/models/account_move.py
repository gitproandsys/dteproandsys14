
from odoo import fields, models, _
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)

SII_VAT = '60805000-0'

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _check_document_types_post(self):
        for rec in self.filtered(
                lambda r: r.company_id.country_id.code == "CL" and
                          r.journal_id.type in ['sale', 'purchase']):
            tax_payer_type = rec.partner_id.l10n_cl_sii_taxpayer_type
            vat = rec.partner_id.vat
            country_id = rec.partner_id.country_id
            latam_document_type_code = rec.l10n_latam_document_type_id.code
            if (not tax_payer_type or not vat) and (country_id.code == "CL" and latam_document_type_code
                                                    and latam_document_type_code not in ['35', '38', '39', '41']):
                raise ValidationError(_('Tax payer type and vat number are mandatory for this type of '
                                        'document. Please set the current tax payer type of this customer'))
            if rec.journal_id.type == 'sale' and rec.journal_id.l10n_latam_use_documents:
                if country_id and country_id.code != "CL":
                    if latam_document_type_code:
                        if not ((tax_payer_type == '4' and latam_document_type_code in ['110', '111', '112']) or (
                                tax_payer_type == '3' and latam_document_type_code in ['39', '41', '61', '56'])):
                            logger.info('PAIS')
                            logger.info(country_id.code)
                            logger.info('latam_document_type_code')
                            logger.info(latam_document_type_code)
                            raise ValidationError(_(
                                'Document types for foreign customers must be export type (codes 110, 111 or 112) or you \
                                should define the customer as an end consumer and use receipts (codes 39 or 41)'))
            if rec.journal_id.type == 'purchase' and rec.journal_id.l10n_latam_use_documents:
                if vat != SII_VAT and latam_document_type_code == '914':
                    raise ValidationError(_('The DIN document is intended to be used only with RUT 60805000-0'
                                            ' (Tesorería General de La República)'))
                if not tax_payer_type or not vat:
                    if country_id.code == "CL" and latam_document_type_code not in [
                        '35', '38', '39', '41']:
                        raise ValidationError(_('Tax payer type and vat number are mandatory for this type of '
                                                'document. Please set the current tax payer type of this supplier'))
                if tax_payer_type == '2' and latam_document_type_code not in ['70', '71', '56', '61']:
                    raise ValidationError(_('The tax payer type of this supplier is incorrect for the selected type'
                                            ' of document.'))
                if tax_payer_type in ['1', '3']:
                    if latam_document_type_code in ['70', '71']:
                        raise ValidationError(_('The tax payer type of this supplier is not entitled to deliver '
                                                'fees documents'))
                    if latam_document_type_code in ['110', '111', '112']:
                        raise ValidationError(_('The tax payer type of this supplier is not entitled to deliver '
                                                'imports documents'))
                if tax_payer_type == '4' or country_id.code != "CL":
                    raise ValidationError(_('You need a journal without the use of documents for foreign '
                                            'suppliers'))
            #if rec.journal_id.type == 'purchase' and not rec.journal_id.l10n_latam_use_documents:
            #    if tax_payer_type != '4':
            #        raise ValidationError(_('This supplier should be defined as foreigner tax payer type and '
            #                                'the country should be different from Chile to register purchases.'))

    din_id = fields.Many2one('account.din', 'DIN', states={'draft': [('readonly', False)]})
    landed_cost_id = fields.Many2one('stock.landed.cost', 'Incomex Folder', ondelete='cascade')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    din_id = fields.Many2one('account.din', 'DIN', related='move_id.din_id', ondelete='set null', index=True, store=True)

