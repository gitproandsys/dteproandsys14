# -*- coding: utf-8 -*-

import datetime, pytz
from .. tools.api import factual
from collections import OrderedDict
from odoo import models, fields, api, exceptions


class CesionFacturasDTE(models.TransientModel):
    _name = 'cesion.facturas'

    partner_id = fields.Many2one('res.partner', 'Cesionario', domain="[('cesionario','=',True)]", required=True)
    company_id = fields.Many2one('res.company', 'Compañia', required=True,
                                 default=lambda self: self.env.user.company_id.id)
    amount_cesion = fields.Float(string="Monto a Ceder", required=True)

    def cesion_facturas(self):
        cesion = OrderedDict()
        context = self._context or {}
        stgo = pytz.timezone('America/Santiago')
        invoice_pool = self.env['account.move']
        wizard = self
        if 'active_id' in context:
            inv_ids = context['active_id']
        else:
            inv_ids = [inv.id for inv in wizard.invoice_ids]
        for invoice in invoice_pool.browse(inv_ids):
            if (stgo.localize(datetime.datetime.today())).strftime('%Y-%m-%d') > invoice.invoice_date_due:
                raise exceptions.Warning('Error!', 'No se puede ceder la factura folio: ' + str(invoice.name) +
                                         ', ya que su fecha de vencimiento a expirado.')

            if invoice.l10n_latam_document_type_id.code not in ['33', '34', '40', '46']:
                raise exceptions.Warning('Error!', 'No se puede ceder la factura folio: ' + str(invoice.name) + \
                                         '. Solo son cedibles las facturas afectas, exentas, factura de compra o liquidacion de factura.')

            cesion['DocumentId'] = invoice.dte_track
            if invoice.residual >= wizard.amount_cesion:
                cesion['Amount'] = wizard.amount_cesion
            else:
                raise exceptions.Warning('El momto a ceder no puede ser mayor a ' + str(invoice.amount_residual))
            cesion['RutCedente'] = invoice.company_id.partner_id.vat
            if invoice.company_id.partner_id.email_cesor:
                cesion['EmailContacto'] = invoice.company_id.partner_id.email_cesor
            else:
                raise exceptions.Warning('Error!',
                                         "Para ceder un documento se necesita el un correo en el campo 'Email Cesor' del partner asociado a su empresa.")
            cesion['NombreContacto'] = invoice.company_id.partner_id.name
            cesion['FonoContacto'] = invoice.company_id.partner_id.phone or invoice.company_id.partner_id.mobile

            if not wizard.partner_id.vat:
                raise exceptions.Warning('Error!', 'You must set a Rut for the selected partner.')
            else:
                cesion['RutCesionario'] = wizard.partner_id.vat
            cesion['RazonSocialCesionario'] = wizard.partner_id.name
            if wizard.partner_id.street and wizard.partner_id.street2:
                cesion['DireccionCesionario'] = '%s %s' % (wizard.partner_id.street, wizard.partner_id.street2)
            elif wizard.partner_id.street:
                cesion['DireccionCesionario'] = wizard.partner_id.street
            elif wizard.partner_id.street2:
                cesion['DireccionCesionario'] = wizard.partner_id.street2
            else:
                raise exceptions.Warning('Error!', 'You must set a street for the selected partner.')
            if not wizard.partner_id.email_dte:
                raise exceptions.Warning('Error!', 'You must set an email for the selected partner.')
            else:
                cesion['EmailCesionario'] = wizard.partner_id.email_dte

            res = factual.send_transfer_dte(wizard.company_id.dte_url, cesion, user=wizard.company_id.dte_user, passwd=wizard.company_id.dte_pass)

            if not res['Status'] or res['Status'] != 1:
                if res['ValidationErrors'] and res['Description']:
                    error = """%s \n%s""" % (res['ValidationErrors'][0], res['Description'])
                elif res['ValidationErrors']:
                    error = """%s""" % (res['ValidationErrors'][0])
                elif res['Description']:
                    error = """%s""" % (res['Description'])
                else:
                    error = ''
                invoice.write({'para_ceder': True, 'transfer_to_id': wizard.partner_id.id,
                               'transfer_failed_text': error})
            else:
                invoice.write({'waiting_cesion': True, 'para_ceder': True,
                               'transfer_failed_text': None, 'transfer_to_id': wizard.partner_id.id,
                               'transfer_track_id': res['TransferTrackId']})
        return True
