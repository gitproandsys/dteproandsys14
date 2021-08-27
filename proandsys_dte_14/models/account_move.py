# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, exceptions, _
from odoo import SUPERUSER_ID
from odoo import netsvc
from odoo.tools import float_compare
from collections import OrderedDict
from datetime import datetime, time, date, timedelta
from .. tools.api import factual
import time, math, os, base64
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

import logging
logger = logging.getLogger(__name__)


class AccountTaxDte(models.Model):
    _inherit = 'account.tax'
    
    recupera = fields.Selection([('1', 'IVA Recuperable'), ('2', 'IVA no Recuperable'), ('3', 'Otros NO recuperable'),
                                 ('4', 'Otros Recuperable')])
    tasa_sii = fields.Float('Tasa Sii', digits=(2, 3))
    

class AccountMoveDte(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_default_forma(self):
        forma_pago = self.env['l10n_cl_dte.payment_type'].search([('code', '=', 'PE')], limit=1)
        return forma_pago

    def get_dte_info(self):
        for invoice in self:
            res = factual.get_dte_info(invoice.company_id.dte_url, invoice.company_id.partner_id.vat, \
                                       invoice.l10n_latam_document_type_id.code, \
                                       str(invoice.name), user=invoice.company_id.dte_user,
                                       passwd=invoice.company_id.dte_pass)
            print("res   =====>>>>    "), res
            if res['Status'] and res['Status'] == 1:
                data = {
                    'dte_status': res['Status'],
                    'ted_xml': res['TedXml'],
                    'pdf_img': res['TedImageBase64'],
                    'get_data': True,
                    'failed_text': None,
                    'sii_failed_text': None,
                    'dte_track': res['TrackId'],
                    'state_dte': 'dte_acepted',
                }
                invoice.write(data)
            else:
                raise exceptions.Warning(res['Description'])
        return True

    def get_acks(self):
        for invoice in self:
            status = factual.get_status(invoice.company_id.dte_url, invoice.dte_track, user=invoice.company_id.dte_user,
                                        passwd=invoice.company_id.dte_pass)
            if status['Approved']:
                if status['CommertialAck']:
                    if status['CommertialAckStatus'] == 0:
                        invoice.write({'comercial_ack': True})
                    elif status['CommertialAckStatus'] == 1:
                        invoice.write({'comercial_ack': True, \
                                    'comercial_ack_text': status['CommertialAckInfo']})
                        print("aprobado con reparos:"), status['CommertialAckInfo']
                    else:
                        invoice.write( \
                            {'comercial_ack_text': status['CommertialAckInfo']})
                        print("Rechazado:"), status['CommertialAckInfo']
                if status['ReceptionAck']:
                    invoice.write({'reception_ack': True})
                if status['ReceptionAckInfo']:
                    invoice.write({'reception_ack_text': status['ReceptionAckInfo']})
                    print(status['ReceptionAckInfo'])
            else:
                raise exceptions.Warning(
                    'Datos' + str(status['Approved']) + 'comercial_a' + str(
                        status['CommertialAck']) + 'reception_a' + str(
                        status['ReceptionAck']))
        return True

    def _get_attachment_values(self, obj, attachment, type=None):
        if obj.move_type == 'out_invoice':
            if obj.l10n_latam_document_type_id.code not in ['35', '38', '39', '41']:
                nombre = 'Factura'
            else:
                nombre = 'Boleta'
        else:
            nombre = 'Nota de Credito'
    
        return {
            'name': '%s.%s_%s%s' % (obj.l10n_latam_document_type_id.code, nombre, obj.name, type if type else '.pdf'),
            'res_name': '%s.%s_%s%s' % (obj.l10n_latam_document_type_id.code, \
                                        nombre, obj.name, type if type else '.pdf'),
            'res_model': 'account.move',
            'res_id': obj.id,
            'datas': attachment,
            'type': 'binary'
        }

    def pdf_interno(self, invoice):
        for record in self:
            old_attch_ids = []
            ir_pool = self.env['ir.attachment']
            ir_actions_report = self.env['ir.actions.report.xml']
            # PDF Normal
            matching_reports = ir_actions_report.search([('name', '=', 'FacturaDTE')])
            if matching_reports:
                report = ir_actions_report.browse(matching_reports[0])
                report_service = 'report.' + report.report_name
                service = netsvc.LocalService(report_service)
                (result, format) = service.create([invoice.id], {'ids': [], 'model': 'account.move'})
                eval_context = {'time': time, 'object': invoice}
                if not report.attachment or not eval(report.attachment, eval_context):
                    # no auto-saving of report as attachment, need to do it manually
                    result = base64.b64encode(result)
                    attch_vals = record._get_attachment_values(invoice, result, type='.pdf')
                    old_pdf_id = ir_pool.search([('name', '=', attch_vals['name']), ('res_model', '=', 'account.move')])
                    if old_pdf_id:
                        old_attch_ids.append(old_pdf_id[0])
                    ir_pool.create(attch_vals)
            # XML Normal
            get_dte = factual.get_dte(invoice.company_id.dte_url, invoice.dte_track, user=invoice.company_id.dte_user,
                                      passwd=invoice.company_id.dte_pass)
            if not get_dte:
                raise exceptions.Warning('No se ha podido obtener el XML.')
            if 'EnvioDte' in get_dte:
                if get_dte['EnvioDte']:
                    attch_vals_xml = record._get_attachment_values(invoice, get_dte['EnvioDte'], type='.xml')
                    old_xml_id = ir_pool.search([('name', '=', attch_vals_xml['name']), \
                                                 ('res_model', '=', 'account.move')])
                    if old_xml_id:
                        old_attch_ids.append(old_xml_id[0])
                    ir_pool.create(attch_vals_xml)
        
            if old_attch_ids:
                ir_pool.unlink(old_attch_ids)
            return True

    def pdf_factual(self, invoice):
        for record in self:
            old_attch_ids = []
            ir_pool = self.env['ir.attachment']
        
            # PDF Normal
            pdf = base64.encodestring(factual.get_pdf(invoice.company_id.dte_url, invoice.dte_track))
            if not pdf:
                raise exceptions.Warning('No se ha podido obtener el PDF.')
            attch_vals = record._get_attachment_values(invoice, pdf, type='.pdf')
            old_pdf_id = ir_pool.search([('name', '=', attch_vals['name']), ('res_model', '=', 'account.move')])
            if old_pdf_id:
                old_attch_ids.append(old_pdf_id[0])
            ir_pool.create(attch_vals)
        
            # XML Normal
            get_dte = factual.get_dte(invoice.company_id.dte_url, invoice.dte_track, user=invoice.company_id.dte_user,
                                      passwd=invoice.company_id.dte_pass)
            if not get_dte:
                raise exceptions.Warning('No se ha podido obtener el XML.')
            if 'EnvioDte' in get_dte:
                if get_dte['EnvioDte']:
                    attch_vals_xml = record._get_attachment_values(invoice, get_dte['EnvioDte'], type='.xml')
                    old_xml_id = ir_pool.search([('name', '=', attch_vals_xml['name']), ('res_model', '=', 'account.move')])
                    if old_xml_id:
                        old_attch_ids.append(old_xml_id[0])
                    ir_pool.create(attch_vals_xml)
        
            # PDF Cedible])
            pdf_cedible = base64.encodestring(factual.get_pdf_cedible(invoice.company_id.dte_url, invoice.dte_track))
            if not pdf_cedible:
                raise exceptions.Warning('No se ha podido obtener el PDF cedible.')
            attch_vals_cedible = record._get_attachment_values(invoice, pdf_cedible, type='_cedible.pdf')
            old_pdf_cedible_id = ir_pool.search([('name', '=', attch_vals_cedible['name']), ('res_model', '=', 'account.move')])
            if old_pdf_cedible_id:
                old_attch_ids.append(old_pdf_cedible_id[0])
            ir_pool.create(attch_vals_cedible)
        
            # XML Transferencia
            if invoice.transfer_track_id:
                get_dte_transfer = factual.get_transfer_dte(invoice.company_id.dte_url, invoice.transfer_track_id, \
                                                            user=invoice.company_id.dte_user,
                                                            passwd=invoice.company_id.dte_pass)
                if not get_dte_transfer:
                    raise exceptions.Warning('No se ha podido obtener el XML de Transferencia.')
                if 'TransferDteXml' in get_dte_transfer:
                    if get_dte_transfer['TransferDteXml']:
                        attch_vals_xml_transfer = record._get_attachment_values(invoice, \
                                                                              get_dte_transfer['TransferDteXml'],
                                                                              type='_cesion.xml')
                        old_xml_cedible_id = ir_pool.search([('name', '=', attch_vals_xml_transfer['name']), \
                                                             ('res_model', '=', 'account.move')])
                        if old_xml_cedible_id:
                            old_attch_ids.append(old_xml_cedible_id[0])
                        ir_pool.create(attch_vals_xml_transfer)
        
            for record in old_attch_ids:
                record.unlink()
            return True

    def get_pdf(self):
        for invoice in self:
            if invoice.company_id.internal_pdf:
                invoice.pdf_interno(invoice)
            else:
                invoice.pdf_factual(invoice)
            return True

    def get_validation(self):
        for invoice in self:
            get_dte = factual.get_dte(invoice.company_id.dte_url, invoice.dte_track, user=invoice.company_id.dte_user,
                                      passwd=invoice.company_id.dte_pass)
            if get_dte['Status'] and get_dte['Status'] == 1:
                status = factual.get_status(invoice.company_id.dte_url, invoice.dte_track, user=invoice.company_id.dte_user,
                                            passwd=invoice.company_id.dte_pass)
                if status['Approved']:
                    invoice.write({'sii_failed_text': None, 'sii_track_id': status['SiiTrackId']})
                
                    f_ids = self.env['l10n_cl_dte.folio_history'].search( \
                        [('type_id', '=', invoice.l10n_latam_document_type_id.id), ('active', '=', True)])
                    if f_ids:
                        f_obj = f_ids[0]
                        if (f_obj.end_folio - f_obj.next_value) < 10:
                            print('Quedan pocos folios para el tipo de documento seleccionado.')
                    else:
                        raise exceptions.Warning(
                            'Ha ocurrido un error al buscar los folios, favor contacte con la mesa de ayuda.')
                
                    invoice.write({'state_dte': 'dte_acepted'})
                else:
                    logger.info("status =======>>>>>   %s" % status)
                    error = status['Comments']
                    if error == 'Operation was Successful':
                        error = False
                    invoice.write({'sii_failed_text': status['Comments'], 'sii_track_id': status['SiiTrackId']})
                    if status['Comments']:
                        invoice.write({'state_dte': 'dte_failed'})
            else:
                invoice.write({'sii_failed_text': get_dte['Description']})
        
            return True

    def get_transfer_validation(self):
        for inv in self:
            res = factual.get_status_transfer(inv.company_id.dte_url, inv.transfer_track_id, user=inv.company_id.dte_user,
                                              passwd=inv.company_id.dte_pass)
            if not res['Status'] or res['Status'] != 1:
                if res['Description']:
                    error = """%s""" % (res['Description'])
                else:
                    error = ''
            
                inv.write({'transfer_failed_text': error, 'waiting_cesion': False})
            else:
                inv.write({'cesion': True, 'waiting_cesion': False})
                inv.get_pdf()
        return True

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        super(AccountMoveDte, self)._compute_amount()
        for record in self:
            amount_exent = 0.0
            amount_untaxed = 0.0
            amount_tax = 0.0
            amount_no_rec = 0.0
            amount_otros = 0.0
            amount_otros_rec = 0.0
            amount_total = 0.0
            if record.invoice_line_ids:
                record.amount_exent = sum(line.price_subtotal or 0 for line in record.invoice_line_ids \
                                        if line.tax_ids and all(line_tax.description in ['EXEV', 'EXEC']
                                                                             for line_tax in line.tax_ids))
        
                record.amount_neto_act_fijo = 0.00
                record.amount_iva_act_fijo = 0.00
        
                record.amount_untaxed = sum(line.price_subtotal for line in record.invoice_line_ids) - record.amount_exent
                record.amount_tax = sum(line.price_subtotal * (line.tax_ids[0].amount/100) for line in record.invoice_line_ids if line.tax_ids and line.tax_ids[0].recupera == '1')
                record.amount_no_rec = sum(line.price_subtotal * (line.tax_ids[0].amount/100) for line in record.invoice_line_ids if line.tax_ids and line.tax_ids[0].recupera == '2')
                record.amount_otros = sum(line.price_subtotal * (line.tax_ids[0].amount/100) for line in record.invoice_line_ids if line.tax_ids and line.tax_ids[0].recupera == '3')
                record.amount_otros_rec = sum(line.price_subtotal * (line.tax_ids[0].amount/100) for line in record.invoice_line_ids if line.tax_ids and line.tax_ids[0].recupera == '4')
                record.amount_total = record.amount_exent + record.amount_untaxed + record.amount_tax + record.amount_no_rec + record.amount_otros + record.amount_otros_rec

    def validar_dte(self):
        for invoice in self:
            if not invoice.invoice_line_ids:
                raise exceptions.Warning('Debe existir al menos una linea en la factura.')
            for line in invoice.invoice_line_ids:
                if not all(line.tax_ids):
                    raise exceptions.Warning('Una de las lineas de la factura no tiene impuesto definido.')
            if invoice.company_id.ind_folios == '2' and invoice.dte and not invoice.internal_folio:
                f_id = self.env['l10n_cl_dte.folio_history'].search(
                    [('company_id', '=', invoice.company_id.id), ('active', '=', True),
                     ('type_id', '=', invoice.l10n_latam_document_type_id.id)])
                if not invoice.old_number:
                    if f_id:
                        f_obj = f_id[0]
                        if (f_obj.end_folio - f_obj.next_value + 1) < 0:
                            raise exceptions.Warning('Ya no tiene mas folios para emitir documentos de este tipo.')
                    else:
                        raise exceptions.Warning(
                            'No se han encontrado registros de folios activos para %s. Favor verificar' % invoice.l10n_latam_document_type_id.name)
            else:
                f_id = self.env['internal.folio'].search(
                    [('company_id', '=', invoice.company_id.id),
                     ('l10n_latam_document_type_id', '=', invoice.l10n_latam_document_type_id.id)], limit=1)
                if not f_id:
                    raise exceptions.Warning('No hay definido Folio Interno para este tipo de Documento.')
            if not invoice.invoice_date:
                raise exceptions.Warning('Hay una factura sin fecha asignada')
            if not invoice.company_id.partner_id.vat:
                raise exceptions.Warning(
                    'Debe Configurar su Rut en el menu de companias para emitir documentos electronicos')
            if not invoice.company_id.partner_id.name:
                raise exceptions.Warning('Debe Configurar su Nombre en el menu de companias')
            if not invoice.company_id.partner_id.giro:
                raise exceptions.Warning('Debe Configurar su Giro en el menu de companias')
            if not invoice.company_id.partner_id.economic_act_ids:
                raise exceptions.Warning('Debe Configurar su Actividad Economica en el menu de companias')
            if not (invoice.company_id.partner_id.phone or invoice.company_id.partner_id.mobile):
                raise exceptions.Warning('Debe Configurar un numero telefonico en el menu de companias')
            if not invoice.company_id.partner_id.street:
                raise exceptions.Warning('Debe Configurar su Direccion en el menu de companias')
            if not invoice.company_id.partner_id.state_id:
                raise exceptions.Warning('Debe Configurar su comuna en el menu de companias')
            if not invoice.company_id.partner_id.city:
                raise exceptions.Warning('Debe Configurar su ciudad en el menu de companias')
            partner = (invoice.partner_invoice_id or invoice.partner_id)
            partner_shipping = (invoice.partner_shipping_id or invoice.partner_id)
            if not invoice.partner_id.vat:
                if invoice.l10n_latam_document_type_id.code not in ['39', '61']:
                    raise exceptions.Warning('El Cliente %s no tiene Rut' % invoice.partner_id.name)
            if not invoice.partner_id.name:
                raise exceptions.Warning('El cliente no tiene nombre nombre')
            if not invoice.partner_id.giro:
                if invoice.l10n_latam_document_type_id.code not in ['39', '61']:
                    raise exceptions.Warning('El Cliente %s no tiene Giro' % invoice.partner_id.name)
            if not invoice.partner_id.street:
                raise exceptions.Warning('El Cliente %s no tiene Direccion' % invoice.partner_id.name)
            if not invoice.partner_id.state_id:
                raise exceptions.Warning('El Cliente %s no tiene Comuna' % invoice.partner_id.name)
            if not invoice.partner_id.city:
                raise exceptions.Warning('El Cliente %s no tiene Ciudad' % invoice.partner_id.name)
            if invoice.l10n_latam_document_type_id.code not in ['39', '61']:
                if not partner.street:
                    raise exceptions.Warning('El Cliente %s no tiene Direccion' % partner.name)
                if not partner.state_id:
                    raise exceptions.Warning('El Cliente %s no tiene Comuna' % partner.name)
                if not partner.city:
                    raise exceptions.Warning('El Cliente %s no tiene Ciudad' % partner.name)
                if not partner_shipping.street:
                    raise exceptions.Warning('El Cliente %s no tiene Direccion' % partner_shipping.name)
                if not partner_shipping.state_id:
                    raise exceptions.Warning('El Cliente %s no tiene Comuna' % partner_shipping.name)
                if not partner_shipping.city:
                    raise exceptions.Warning('El Cliente %s no tiene Ciudad' % partner_shipping.name)
            if invoice.l10n_latam_document_type_id.code == 61 and not invoice.reference_lines:
                raise exceptions.Warning('No se puede validar una nota de credito sin un documento de referencia.')
            if invoice.l10n_latam_document_type_id.code == 61 and invoice.move_type not in ['out_refund', 'in_refund']:
                raise exceptions.Warning('No se puede validar una nota de credito con tipo interno Factura.')
            return

    def _get_ref_lines(self, ref):
        reference = OrderedDict()
        dte_references = []
        cont = 1
        for line in ref:
            if line.ref_reason == '1':
                ref_reason = 'Sobreescribe Documento'
            elif line.ref_reason == '2':
                ref_reason = 'Corrige Texto'
            elif line.ref_reason == '3':
                ref_reason = 'Corrige Monto'
            else:
                ref_reason = ''
            reference['NroLinRef'] = cont
            reference['TpoDocRef'] = line.tpo_doc_ref.code
            reference['FolioRef'] = line.ref_folio
            reference['FchRef'] = line.ref_date
            reference['CodRef'] = line.ref_reason and line.ref_reason or ''
            reference['RazonRef'] = ref_reason
            reference['ExternalDocument'] = line.external_document
            cont += 1
            dte_references.append(reference.copy())
        return dte_references

    def _get_dte_lines(self, lines):
        for invoice in self:
            codes = OrderedDict()
            detail = OrderedDict()
            dte_details = []
        
            cont = 1
            for line in lines:
                if line.price_unit > 0:
                    codes['TpoCodigo'] = 'EAN' if line.product_id.barcode else 'Interna'
                    codes['VlrCodigo'] = line.product_id.barcode or line.product_id.default_code or ''
                    dte_codes = [codes.copy()]
                
                    detail['NroLinDet'] = cont
                    detail['CdgItems'] = dte_codes
                    detail['NmbItem'] = line.product_id and line.product_id.name[:80] or line.name.replace('\n', ' ')[:80]
                    detail['DscItem'] = line.name.replace('\n', ' ')[:80]
                    detail['QtyItem'] = round(line.quantity, 3)
                    detail['Subcantidades'] = []
                    detail['UnmdItem'] = line.product_uom_id.name[:4]
                
                    taxs_rate = 0
                    for tax_line in line.tax_ids:
                        if tax_line.price_include:
                            taxs_rate += taxs_rate + (tax_line.amount/100)
                        if tax_line.recupera == '4':
                            detail['CodImpAdic'] = tax_line.l10n_cl_code
                
                    if taxs_rate > 0:
                        if invoice.l10n_latam_document_type_id.code != '39':
                            detail['PrcItem'] = round(line.price_unit / (1 + taxs_rate), 4)
                        else:
                            detail['PrcItem'] = line.price_unit
                    else:
                        detail['PrcItem'] = line.price_unit
                
                    detail['DescuentoPct'] = line.discount
                    detail['DescuentoMonto'] = round(
                        detail['QtyItem'] * detail['PrcItem'] * (line.discount or 0.0) / 100.0, 0)
                    detail['MontoItem'] = line.price_subtotal
                    if line.ind_exencion != '7' and line.ind_exencion:
                        detail['IndExe'] = int(line.ind_exencion)
                
                    for i in line.tax_ids:
                        if i.name == 'EXENTO' and line.ind_exencion != 1:
                            raise exceptions.Warning(
                                'Los items exentos debem estar en No Afecto o exento de IVA en el indicador de exencion.')
                    cont += 1
                    dte_details.append(detail.copy())
            return dte_details

    def _get_dte_discounts(self, lines):
        discounts = OrderedDict()
        cont = 1
        disc = 0.00
        for line in lines:
            if line.price_unit < 0:
                disc += line.price_unit
        discounts['NroLinDR'] = cont
        discounts['TpoMov'] = 'D'
        discounts['TpoValor'] = "$"
        discounts['ValorDR'] = -(round(disc, 2))
        return discounts

    def send_dte(self):
        dte = OrderedDict()
        global_discount = 0
        for invoice in self:
            if invoice.move_type not in ['out_invoice', 'out_refund'] or not invoice.dte:
                continue
            if invoice.get_data:
                invoice.write({'failed_text': None, 'sii_failed_text': None, 'dte_status': 1})
                return True
            if invoice.company_id.ind_folios == '2' and invoice.dte:
                f_id = self.env['l10n_cl_dte.folio_history'].search(
                    [('company_id', '=', invoice.company_id.id), ('active', '=', True),
                     ('type_id', '=', invoice.l10n_latam_document_type_id.id)])
            else:
                f_id = self.env['internal.folio'].search(
                    [('company_id', '=', invoice.company_id.id),
                     ('l10n_latam_document_type_id', '=', invoice.l10n_latam_document_type_id.id)], limit=1)
                
            dte_reference = invoice._get_ref_lines(invoice.reference_lines)
            dte_detail = invoice._get_dte_lines(invoice.invoice_line_ids)
            dte_discount = invoice._get_dte_discounts(invoice.invoice_line_ids)
            dte['TipoDTE'] = invoice.l10n_latam_document_type_id.code
            if invoice.old_number:
                dte['Folio'] = invoice.old_number
            else:
                if invoice.company_id.ind_folios == '2' and invoice.dte:
                    dte['Folio'] = self.env['l10n_cl_dte.folio_history'].folio_consume(f_id[0].id)
            dte['FchEmis'] = invoice.invoice_date
            dte['IndNoRebaja'] = 1 if invoice.l10n_latam_document_type_id.code in ('55', '60') and invoice.no_rebaja else 0
            if invoice.l10n_latam_document_type_id.code in ['35', '38', '39', '41']:
                dte['IndServicio'] = invoice.ind_servicio
            else:
                invoice.ind_servicio = False
            dte['TipoDespacho'] = invoice.tipo_despacho_id.code or 0
            if invoice.invoice_date_due:
                dte['FchVenc'] = invoice.invoice_date_due
            else:
                raise exceptions.Warning(
                    'Debe definir el plazo de pago o en su defecto la fecha de vencimiento de la factura y volver a validar')
            dte['RUTEmisor'] = invoice.company_id.partner_id.vat
            dte['RznSocEmisor'] = invoice.company_id.partner_id.name
            if invoice.company_id.partner_id.giro:
                dte['GiroEmis'] = invoice.company_id.partner_id.giro[:80] or ''
            dte['Acteco'] = int(invoice.company_id.partner_id.economic_act_ids[0].code)
            dte['Telefono'] = str(invoice.company_id.partner_id.phone or '') + ',' + str(
                invoice.company_id.partner_id.mobile or '')
            dte['DirOrigen'] = str(invoice.company_id.partner_id.street or '') + ' ' + str(
                invoice.company_id.partner_id.street2 or '')
            if invoice.company_id.partner_id.state_id.name:
                dte['CmnaOrigen'] = invoice.company_id.partner_id.state_id.name[:20] or ''
            dte['CiudadOrigen'] = invoice.company_id.partner_id.city
            doc_origen = False
            if invoice.invoice_origin:
                doc_origen = self.env['account.move'].search([('name', '=', invoice.invoice_origin)])
            if invoice.l10n_latam_document_type_id.code in ['39'] or (doc_origen and doc_origen.l10n_latam_document_type_id.code in ['39']):
                dte['RUTRecep'] = '66666666-6'
            else:
                if invoice.partner_id.vat:
                    dte['RUTRecep'] = invoice.partner_id.vat
            dte['CdgIntRecep'] = invoice.partner_id.ref or None
            if invoice.partner_id.name:
                dte['RznSocRecep'] = invoice.partner_id.name[:100] or ''
            partner = (invoice.partner_invoice_id or invoice.partner_id)
            partner_des = (invoice.partner_shipping_id or invoice.partner_id)
            if invoice.partner_id.giro:
                dte['GiroRecep'] = invoice.partner_id.giro[:40] or ''
            dte['Contacto'] = invoice.company_id.partner_id.email_dte
            if partner.street or partner.street2:
                dte['DirRecep'] = str(partner.street or '') + ' ' + str(partner.street2 or '')[:70] or ''
            if partner.state_id.name:
                dte['CmnaRecep'] = partner.state_id.name[:20] or ''
            dte['CiudadRecep'] = partner.city
            dte['DirDest'] = str(partner_des.street or '') + ' ' + str(partner_des.street2 or '')
            if partner_des.state_id.name:
                dte['CmnaDest'] = partner_des.state_id.name[:20] or ''
            dte['CiudadDest'] = partner_des.city
            for line_invoice in invoice.invoice_line_ids:
                if line_invoice.price_unit < 0:
                    global_discount += line_invoice.price_unit
            if invoice.l10n_latam_document_type_id.code in ['39']:
                dte['MntNeto'] = 0
                dte['MntExe'] = 0
            else:
                dte['MntNeto'] = int(round(invoice.amount_untaxed, 0))
                if invoice.amount_exent > 0:
                    dte['MntExe'] = int(round(invoice.amount_exent, 0))
                else:
                    dte['MntExe'] = 0
            detail_impuestos = OrderedDict()
            impuestos = []
            for tax_line in invoice.l10n_latam_tax_ids:
                if tax_line.tax_line_id.recupera == '4':
                    detail_impuestos['TipoImp'] = tax_line.tax_line_id.l10n_cl_code
                    detail_impuestos['TasaImp'] = int(tax_line.tax_line_id.tasa_sii)
                    balance = tax_line.balance if tax_line.balance > 0 else -tax_line.balance
                    detail_impuestos['MontoImp'] = balance
                    impuestos.append(detail_impuestos.copy())
                if tax_line.balance != 0:
                    if tax_line.tax_line_id.recupera in ['1' , '2']:
                        if invoice.l10n_latam_document_type_id.code != '39':
                            balance = tax_line.balance if tax_line.balance > 0 else -tax_line.balance
                            dte['IVA'] = int(round(balance, 0))
                        else:
                            dte['IVA'] = 0
                    else:
                        dte['IVA'] = 0
            dte['ImptoReten'] = impuestos
            dte['TasaIVA'] = 19.00 if invoice.l10n_latam_document_type_id.code != '34' else 0
            dte['MntTotal'] = int(round(invoice.amount_total, 0))
            dte['TermPagoGlosa'] = invoice.invoice_payment_term_id.name if invoice.invoice_payment_term_id else ''
            dte['Referencias'] = dte_reference
            dte['Detalles'] = dte_detail
            dte['DescuentosGlobales'] = dte_discount
            dte['Extensiones'] = {'Web': invoice.company_id.partner_id.website}
            if invoice.user_id:
                dte['Extensiones'].update({'Vendedor': invoice.user_id.name})
            if invoice.partner_id.phone:
                dte['Extensiones'].update({'Fono': invoice.partner_id.phone})
            logger.info(dte)
            logger.info('URL')
            logger.info(invoice.company_id.dte_url)
            logger.info('USUARIO')
            logger.info(invoice.company_id.dte_user)
            logger.info('CLAVE')
            logger.info(invoice.company_id.dte_pass)
            if invoice.company_id.ind_folios == '2' and invoice.dte:
                res = factual.send_dte(invoice.company_id.dte_url, dte, invoice.company_id.dte_user, invoice.company_id.dte_pass)
                if not res['Status'] or res['Status'] != 1:
                    if res['ValidationErrors'] and res['Description']:
                        error = """%s \n%s""" % (res['ValidationErrors'][0], res['Description'])
                    elif res['ValidationErrors']:
                        error = """%s""" % (res['ValidationErrors'][0])
                    elif res['Description']:
                        error = """%s""" % (res['Description'])
                    else:
                        error = ''
                    if error == 'Operation was Successful':
                        error = False
                    invoice.write({
                        'dte_status': res['Status'],
                        'name': dte['Folio'],
                        'old_number': dte['Folio'],
                        'failed_text': error,
                        'state_dte': 'dte_failed'})
                else:
                    data = {
                        'dte_status': res['Status'],
                        'name': dte['Folio'],
                        'old_number': dte['Folio'],
                        'ted_xml': res['TedXml'],
                        'pdf_img': res['TedImageBase64'],
                        'failed_text': None,
                        'sii_failed_text': None,
                        'dte_track': res['TrackId'],
                    }
                    invoice.write(data)
                    if invoice.l10n_latam_document_type_id.code not in ['35', '38', '39', '41']:
                        invoice.write({'state_dte': 'dte_waiting'})
                    else:
                        invoice.write({'state_dte': 'dte_acepted'})
            else:
                f_id.write({
                    'sig_folio': f_id.sig_folio + 1
                })
        return True

    def send_internal_folio(self):
        for invoice in self:
            if not invoice.old_number:
                f_id = self.env['internal.folio'].search(
                    [('company_id', '=', invoice.company_id.id),
                     ('l10n_latam_document_type_id', '=', invoice.l10n_latam_document_type_id.id)], limit=1)
                data = {
                    'name': f_id.sig_folio,
                    'old_number': f_id.sig_folio,
                    'dte': False,
                    'internal_folio': True,
                }
                invoice.write(data)
                f_id.write({
                    'sig_folio': f_id.sig_folio + 1
                })
            else:
                if invoice.internal_folio:
                    data = {
                        'dte': False,
                    }
                else:
                    data = {
                        'dte': True,
                    }
                invoice.write(data)
        return True

    def _post(self, soft=True):
        super(AccountMoveDte, self)._post()
        for record in self:
            if record.move_type in ['out_invoice', 'out_refund']:
                if record.state_dte not in ['dte_acepted']:
                    record.validar_dte()
                    if record.company_id.ind_folios == '2' and record.dte and not record.internal_folio:
                        if record.state_dte in ['dte_waiting']:
                            record.get_dte_info()
                        else:
                            record.send_dte()
                    else:
                        record.send_internal_folio()
                else:
                    continue

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        moves = self.filtered(lambda move: move.state == 'posted')
        if not moves:
            return
    
        self.flush(['name', 'journal_id', 'move_type', 'state'])
    
        # /!\ Computed stored fields are not yet inside the database.
        self._cr.execute('''
                SELECT move2.id, move2.name
                FROM account_move move
                INNER JOIN account_move move2 ON
                    move2.name = move.name
                    AND move2.journal_id = move.journal_id
                    AND move2.move_type = move.move_type
                    AND move2.id != move.id
                WHERE move.id IN %s AND move2.state = 'posted'
            ''', [tuple(moves.ids)])
        res = self._cr.fetchall()
        return
        if res:
            raise ValidationError(_('Posted journal entry must have an unique sequence number per company.\n'
                                    'Problematic numbers: %s\n') % ', '.join(r[1] for r in res))
        
    @api.onchange('partner_id')
    def _get_default_contacts(self):
        for record in self:
            record.contacto_invoice_id = False
            record.contacto_collection_id = False
            if record.partner_id.contacto_invoice_id:
                record.contacto_invoice_id = record.partner_id.contacto_invoice_id.id
            else:
                record.contacto_invoice_id = record.partner_id.id
            if record.partner_id.contacto_collection_id:
                record.contacto_collection_id = record.partner_id.contacto_collection_id.id
            else:
                record.contacto_collection_id = record.partner_id.id

    @api.model
    def consult_validate_invoice(self):
        invoices = self.env['account.move'].search([('state_dte', '=', 'dte_waiting')])
        for record in invoices:
            record.get_validation()

    @api.constrains('invoice_line_ids')
    def _check_max_item_invoice(self):
        for record in self:
            if record.l10n_latam_document_type_id:
                if record.l10n_latam_document_type_id.code in ['33', '34', '61', '56']:
                    if len(record.invoice_line_ids) > 60:
                        raise Warning('El valor maximo por factura es de 60 Items para este tipo de documento')
                else:
                    if len(record.invoice_line_ids) > 1000:
                        raise Warning('El valor maximo por factura es de 1000 Items')
            return

    @api.constrains('state', 'l10n_latam_document_type_id')
    def _check_l10n_latam_documents(self):
        """ This constraint checks that if a invoice is posted and does not have a document type configured will raise
        an error. This only applies to invoices related to journals that has the "Use Documents" set as True.
        And if the document type is set then check if the invoice number has been set, because a posted invoice
        without a document number is not valid in the case that the related journals has "Use Docuemnts" set as True """
        validated_invoices = self.filtered(lambda x: x.l10n_latam_use_documents and x.state == 'posted')
        without_doc_type = validated_invoices.filtered(lambda x: not x.l10n_latam_document_type_id)
        return
        """if without_doc_type:
            raise ValidationError(_(
                'The journal require a document type but not document type has been selected on invoices %s.',
                without_doc_type.ids
            ))
        without_number = validated_invoices.filtered(
            lambda x: not x.l10n_latam_document_number and x.l10n_latam_manual_document_number)
        if without_number:account.move.reversal
            raise ValidationError(_(
                'Please set the document number on the following invoices %s.',
                without_number.ids
            ))"""

    @api.constrains('move_type', 'l10n_latam_document_type_id')
    def _check_invoice_type_document_type(self):
        """for rec in self.filtered('l10n_latam_document_type_id.internal_type'):
            internal_type = rec.l10n_latam_document_type_id.internal_type
            invoice_type = rec.move_type
            if self.l10n_latam_document_type_id.code not in ['61'] and invoice_type in ['out_refund', 'in_refund']:
                raise ValidationError(_('You can not use a %s document type with a refund invoice', internal_type))
            elif internal_type == 'credit_note' and invoice_type in ['out_invoice', 'in_invoice']:
                raise ValidationError(_('You can not use a %s document type with a invoice', internal_type))"""
        return

    @api.model
    def cron_xml_compras(self):
        res_pool = self.env['res.company']
        tracks_xml = OrderedDict()
        xml_pool = self.env['l10n_cl_dte.document_xml']
        TrackIds = []
        company = self.env.user.company_id
        rut_xml = company.partner_id.vat
        r = factual.get_documents_xml_info(url=company.dte_url, data=rut_xml, user='81895441-64d5-4ea3-81bb-55e73be4cfbe',
                                           passwd='zKHbvBHeIU1088X')
        if r.get('ReceivedDocuments'):
            for item in r['ReceivedDocuments']:
                dte = base64.b64decode(item.get('EnvioDte'))
                dte2 = str(dte, 'utf-8', 'ignore')
                TrackIds.append(item.get('TrackId'))
                xml_pool.create_doc_webhook(dte2)
            tracks_xml['TrackIds'] = TrackIds
            d = factual.confirm_documents_xml(url=company.dte_url, data=tracks_xml, user='81895441-64d5-4ea3-81bb-55e73be4cfbe',
                                              passwd='zKHbvBHeIU1088X')
        else:
            raise exceptions.Warning(str('No hay documentos'))

    @api.model
    def _move_autocomplete_invoice_lines_create(self, vals_list):
        ''' During the create of an account.move with only 'invoice_line_ids' set and not 'line_ids', this method is called
        to auto compute accounting lines of the invoice. In that case, accounts will be retrieved and taxes, cash rounding
        and payment terms will be computed. At the end, the values will contains all accounting lines in 'line_ids'
        and the moves should be balanced.

        :param vals_list:   The list of values passed to the 'create' method.
        :return:            Modified list of values.
        '''
        new_vals_list = []
        for vals in vals_list:
            if not vals.get('invoice_line_ids'):
                new_vals_list.append(vals)
                continue
            if vals.get('line_ids'):
                vals.pop('invoice_line_ids', None)
                new_vals_list.append(vals)
                continue
            if not vals.get('move_type') and not self._context.get('default_move_type'):
                vals.pop('invoice_line_ids', None)
                new_vals_list.append(vals)
                continue
            vals['move_type'] = vals.get('move_type', self._context.get('default_move_type', 'entry'))
            if not vals['move_type'] in self.get_invoice_types(include_receipts=True):
                new_vals_list.append(vals)
                continue
        
            vals['line_ids'] = vals.pop('invoice_line_ids')
        
            if vals.get('invoice_date') and not vals.get('date'):
                vals['date'] = vals['invoice_date']
        
            ctx_vals = {'default_move_type': vals.get('move_type') or self._context.get('default_move_type')}
            if vals.get('currency_id'):
                ctx_vals['default_currency_id'] = vals['currency_id']
            if vals.get('journal_id'):
                ctx_vals['default_journal_id'] = vals['journal_id']
                # reorder the companies in the context so that the company of the journal
                # (which will be the company of the move) is the main one, ensuring all
                # property fields are read with the correct company
                journal_company = self.env['account.journal'].browse(vals['journal_id']).company_id
                allowed_companies = self._context.get('allowed_company_ids', journal_company.ids)
                reordered_companies = sorted(allowed_companies, key=lambda cid: cid != journal_company.id)
                ctx_vals['allowed_company_ids'] = reordered_companies
            self_ctx = self.with_context(**ctx_vals)
            new_vals = self_ctx._add_missing_default_values(vals)
        
            move = self_ctx.new(new_vals)
            new_vals_list.append(move._move_autocomplete_invoice_lines_values())
    
        return new_vals_list
        
    purchase_xml_id = fields.Many2one('l10n_cl_dte.document_xml', 'XML Compras', copy=False,
                                      domain="[('invoice_asoc_id','=', False),('comercial_state', '=', '1')]")

    state_dte = fields.Selection([('dte_none', 'No Aplica DTE'), ('dte_waiting', 'Por Aprobar DTE'), \
                                  ('dte_failed', 'DTE Fallido'), ('dte_acepted', 'DTE Aceptado')], \
                                 string='Estado DTE', readonly=True, default='dte_none', copy=False)
    ind_servicio = fields.Selection([('1', 'Boletas de servicios periodicos'), ('2', 'Boletas de servicios periodicos'), \
                                     ('3', 'Boletas de venta y servicios'),
                                     ('4', 'Boleta de Espectaculos emitida por cuenta de Terceros')], \
                                    'Indicador de Servicios', default='3', readonly=True, \
                                    states={'draft': [('readonly', False)]}, copy=False)
    dte_status = fields.Integer('Estatus DTE', copy=False)
    dte_track = fields.Char('Track ID Dte', copy=False)
    sii_track_id = fields.Char('SII Track Id', copy=False)
    ted_xml = fields.Text('TED', copy=False)
    
    old_number = fields.Char('Número anterior', size=64, copy=False)
    pdf_img = fields.Binary('Imagen PDF')
    failed_text = fields.Text('Razón del fracaso', copy=False)
    sii_failed_text = fields.Text('Razón del fracaso SII', copy=False)
    
    dte = fields.Boolean('Es un documento DTE?', default=True, readonly=True, states={'draft': [('readonly', False)]})
    internal_folio = fields.Boolean('Es un documento interno?', default=False, readonly=True)
    reception_ack = fields.Boolean('Recepción Ack', default=False, copy=False)
    reception_ack_text = fields.Text('Texto Recepción Ack', copy=False)
    comercial_ack = fields.Boolean('Comercial Ack', default=False, copy=False)
    comercial_ack_text = fields.Text('Texto Comercial Ack', copy=False)
    partner_invoice_id = fields.Many2one(
        'res.partner', 'Dirección de Facturación',
        readonly=False,
        domain="['|',('id','=',partner_id),'&',('parent_id','=',partner_id),('type','=','invoice')]",
        required=False, states={'draft': [('readonly', False)]},
        help="Dirección de facturación de la factura actual.")
    partner_shipping_id = fields.Many2one(
        'res.partner',
        string='Dirección de entrega',
        domain="['|',('id','=',partner_id),'&',('parent_id','=',partner_id),('type','=','delivery')]",
        readonly=False,
        states={'draft': [('readonly', False)]},
        help="Dirección de entrega de la factura actual.")
    contacto_invoice_id = fields.Many2one('res.partner', 'Contacto de Facturación',
                                          domain="[('parent_id','=',partner_id),('type','=','contact')]", readonly=True,
                                          required=False, states={'draft': [('readonly', False)]},
                                          help="Contacto para mandar correo de facturacion.")
    contacto_collection_id = fields.Many2one('res.partner', 'Contacto de Cobranza',
                                             domain="[('parent_id','=',partner_id),('type','=','contact')]",
                                             readonly=True,
                                             required=False, states={'draft': [('readonly', False)]},
                                             help="Contacto para mandar correo de cobranza.")
    ref_ready = fields.Boolean('Referencias listas', default=True, readonly=True, states={'draft': [('readonly', False)]},
                               copy=False)
    reference_lines = fields.One2many('l10n_cl_dte.reference', 'invoice_id', string='Reference Lines', readonly=True,
                                      states={'draft': [('readonly', False)]}, copy=False)

    get_data = fields.Boolean('Obtener Datos', default=False, copy=False)
    
    medio_pago_id = fields.Many2one('l10n_cl_dte.payment_type', 'Medio Pago', default=_get_default_forma)
    # SOLO EN FACTURAS y GUIA DESPACHO DE PRODUCTOS NO SERVICIOS.
    tipo_despacho_id = fields.Many2one('l10n_cl_dte.tipo_despacho', string='Tipo de entrega', readonly=True,
                                       states={'draft': [('readonly', False)]}, copy=False)
    # SOLO PARA FACTURAS Y NOTAS DE CREDITO, DEBITO
    ind_servicio_id = fields.Many2one('l10n_cl_dte.ind_servicio', string='Indicador de Servicio', copy=False,
                                      readonly=True, states={'draft': [('readonly', False)]},
                                      help='Codigo: 4 y 5 SOLO para facturas de exportacion.')
    # OPCIONAL EN GUIA Y FACTURAS EXPORTACION, no se crea ese campo hasta sacar algo
    forma_pago_id = fields.Many2one('l10n_cl_dte.forma_pago', string='Metodo de pago', readonly=True,
                                    states={'draft': [('readonly', False)]}, copy=False)
    cod_no_rec = fields.Selection([('1', 'Compras destinadas a IVA a generar operaciones no gravadas o exentas.'), \
                                   ('2', 'Facturas de proveedores registradas fuera de plazo.'), \
                                   ('3', 'Gastos rechazados'), \
                                   ('4', 'Entregas gratuitas recibidas.'), ('9', 'Otros')])

    ######################################### CAMPOS FUNCION DE LA FACTURA ##################################################
    amount_untaxed = fields.Monetary(string='Neto', digits=dp.get_precision('Account'),
                                  store=True, readonly=True, compute='_compute_amount', tracking=True)
    amount_exent = fields.Monetary(string='Exento', digits=dp.get_precision('Account'),
                                store=True, readonly=True, compute='_compute_amount', tracking=True)
    amount_otros = fields.Monetary(string='Otros Impuestos No Recup', digits=dp.get_precision('Account'),
                                store=True, readonly=True, compute='_compute_amount', tracking=True)
    amount_neto_act_fijo = fields.Monetary(string='Neto Activo Fijo', digits=dp.get_precision('Account'),
                                        store=True, readonly=True, compute='_compute_amount', tracking=True)
    amount_iva_act_fijo = fields.Monetary(string='Iva Activo Fijo', digits=dp.get_precision('Account'),
                                       store=True, readonly=True, compute='_compute_amount', tracking=True)
    amount_no_rec = fields.Monetary(string='IVA no Recuperable', digits=dp.get_precision('Account'),
                                 store=True, readonly=True, compute='_compute_amount', tracking=True)
    amount_otros_rec = fields.Monetary(string='Otros Impuestos Recuperable', digits=dp.get_precision('Account'),
                                    store=True, readonly=True, compute='_compute_amount', tracking=True)

    ####################### Export Invoice #######################
    export_invoice = fields.Boolean('Exportar Facturas?', readonly=True, states={'draft': [('readonly', False)]})
    boleta_honorario = fields.Boolean('Boleta de Honorario', readonly=True, states={'draft': [('readonly', False)]})
    # Campo Obligatorio cuando en "Forma pago exportacion" se indique "anticipo".
    # LLenar al paso del estado cancelado, quitar volver a borrador.
    date_cancel = fields.Datetime('Fecha de cancelación', readonly=True, states={'draft': [('readonly', False)]},
                                  copy=False)
    ##################### Fin Export Invoice #####################

    ##################### Credit Note #####################
    no_rebaja = fields.Boolean('Indicador de No Rebaja', copy=False, readonly=True,
                               states={'draft': [('readonly', False)]},
                               help='Solo para Notas de Credito que no tienen derecho a Rebaja del Debito')
    ################### Fin Credit Note ###################

    ################### Ceder Factura ####################
    cesion = fields.Boolean('Factura Cedida', default=False, copy=False)
    waiting_cesion = fields.Boolean('Esperando Ceder', default=False, copy=False,
                                    help='Esperando respuesta de SII para Ceder Factura.')
    para_ceder = fields.Boolean('Para Ceder', default=False, copy=False)
    transfer_track_id = fields.Char('Transferir Track ID', copy=False)
    transfer_failed_text = fields.Text('Razón del fracaso', copy=False)
    transfer_to_id = fields.Many2one('res.partner', 'Transferir a', copy=False)
    ################# Fin Ceder Factura ##################
    
    reference = fields.Char('Factura Proveedor', copy=False)
    sent_email_cron = fields.Boolean('Omitir envio de correo de cobranza', default=False, copy=False)
    attr_ids = fields.One2many('ir.attachment', 'res_id', string='Adjuntos')
    
    ####### SEND EMAIL ######
    
    def run_cron(self):
        cron = self.env['ir.cron'].search(
            [('name', '=', 'Facturas vencida en dias anteriores')])
        if cron:
            cron.method_direct_trigger()
        return

    def generate_pdf(self):
        pdf = self.env.ref('proandsys_report_14.report_factura_sii')._render_qweb_pdf(self.id)[0]
        attach_id = self.env['ir.attachment'].create({
            'name': 'Factura de cliente',
            'type': 'binary',
            'datas': base64.encodestring(pdf),
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/x-pdf'
        })
        return attach_id

    @api.model
    def invoice_due_before(self):
        param = self.env['ir.config_parameter']
        email_due_before = bool(param.sudo().get_param('email_due_before'))
        if email_due_before:
            invoices = self.env['account.move'].search(
                [('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'in_payment', 'partial']), ('move_type', '=', 'out_invoice'), ('sent_email_cron', '=', False)])
            fecha_act = date.today()
            temp_id = self.env.ref('proandsys_dte_14.email_template_edi_invoice_due_before')
            mail_out_temp = self.env['ir.mail_server'].search([])
            mail_out = self.env['ir.mail_server'].search([])
            email_from_priority = False
            if temp_id.email_from:
                st_mail = temp_id.email_from.find("<") + 1
                end_mail = temp_id.email_from.find(">")
                correo = temp_id.email_from[st_mail:end_mail]
                mail_out_temp = self.env['ir.mail_server'].search([('smtp_user', '=', correo)], limit=1)
                mail_out = self.env['ir.mail_server'].search([('sequence', '=', 1)])
                if mail_out_temp:
                    email_from_priority = mail_out_temp.sequence
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 2})
                    mail_out_temp.write({'sequence': 1})
            for record in invoices:
                if record.invoice_date_due:
                    entered_date = record.invoice_date_due
                    entered_date = entered_date
                    b = entered_date + timedelta(days=1)
                    if fecha_act >= b and record.l10n_latam_document_type_id.code in ['33', '34', 'NV']:
                        #temp_id.send_mail(record.id, True, timeout=50)
                        result = record.generate_pdf()
                        temp_id.attachment_ids = [(6, 0, [result.id])]
                        temp_id.send_mail(record.id, True)
                        time.sleep(30)
            if temp_id.email_from:
                if mail_out_temp:
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 1})
                    mail_out_temp.write({'sequence': email_from_priority})

    @api.model
    def invoice_to_due(self):
        param = self.env['ir.config_parameter']
        email_to_due = bool(param.sudo().get_param('email_to_due'))
        if email_to_due:
            invoices = self.env['account.move'].search(
                [('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'in_payment', 'partial']), ('move_type', '=', 'out_invoice'), ('sent_email_cron', '=', False)])
            fecha_act = date.today()
            temp_id = self.env.ref('proandsys_dte_14.email_template_edi_invoice_due')
            mail_out_temp = self.env['ir.mail_server'].search([])
            mail_out = self.env['ir.mail_server'].search([])
            email_from_priority = False
            if temp_id.email_from:
                st_mail = temp_id.email_from.find("<") + 1
                end_mail = temp_id.email_from.find(">")
                correo = temp_id.email_from[st_mail:end_mail]
                mail_out_temp = self.env['ir.mail_server'].search([('smtp_user', '=', correo)], limit=1)
                mail_out = self.env['ir.mail_server'].search([('sequence', '=', 1)])
                if mail_out_temp:
                    email_from_priority = mail_out_temp.sequence
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 2})
                    mail_out_temp.write({'sequence': 1})
            for record in invoices:
                if record.invoice_date_due:
                    entered_date = record.invoice_date_due
                    entered_date = entered_date
                    a = entered_date - timedelta(days=int(param.sudo().get_param('qty_days')))
                    if fecha_act == a and record.l10n_latam_document_type_id.code in ['33', '34', 'NV']:
                        temp_id.send_mail(record.id, True)
            if temp_id.email_from:
                if mail_out_temp:
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 1})
                    mail_out_temp.write({'sequence': email_from_priority})

    @api.model
    def invoice_due_today(self):
        param = self.env['ir.config_parameter']
        email_due_today = bool(param.sudo().get_param('email_due_today'))
        if email_due_today:
            invoices = self.env['account.move'].search(
                [('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'in_payment', 'partial']), ('move_type', '=', 'out_invoice'), ('sent_email_cron', '=', False)])
            temp_id = self.env.ref('proandsys_dte_14.email_template_edi_invoice_due_today')
            fecha_act = date.today()
            mail_out_temp = self.env['ir.mail_server'].search([])
            mail_out = self.env['ir.mail_server'].search([])
            email_from_priority = False
            if temp_id.email_from:
                st_mail = temp_id.email_from.find("<") + 1
                end_mail = temp_id.email_from.find(">")
                correo = temp_id.email_from[st_mail:end_mail]
                mail_out_temp = self.env['ir.mail_server'].search([('smtp_user', '=', correo)], limit=1)
                mail_out = self.env['ir.mail_server'].search([('sequence', '=', 1)])
                if mail_out_temp:
                    email_from_priority = mail_out_temp.sequence
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 2})
                    mail_out_temp.write({'sequence': 1})
            for record in invoices:
                if record.invoice_date_due:
                    entered_date = record.invoice_date_due
                    entered_date_invoice = record.invoice_date
                    entered_date = entered_date.date()
                    entered_date_invoice = entered_date_invoice.date()
                    b = entered_date
                    a = entered_date_invoice
                    if fecha_act == b and fecha_act != a and record.l10n_latam_document_type_id.code in ['33', '34', 'NV']:
                        temp_id.send_mail(record.id, True)
            if temp_id.email_from:
                if mail_out_temp:
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 1})
                    mail_out_temp.write({'sequence': email_from_priority})

    @api.model
    def invoice_supplier_due_before(self):
        param = self.env['ir.config_parameter']
        email_to_due = bool(param.sudo().get_param('email_to_due_supplier'))
        if email_to_due:
            invoices = self.env['account.move'].search(
                [('state', '=', 'posted'), ('move_type', '=', 'in_invoice')])
            fecha_act = date.today()
            temp_id = self.env.ref('proandsys_dte_14.email_template_invoice_due_supplier')
            mail_out_temp = self.env['ir.mail_server'].search([])
            mail_out = self.env['ir.mail_server'].search([])
            email_from_priority = False
            if temp_id.email_from:
                st_mail = temp_id.email_from.find("<") + 1
                end_mail = temp_id.email_from.find(">")
                correo = temp_id.email_from[st_mail:end_mail]
                mail_out_temp = self.env['ir.mail_server'].search([('smtp_user', '=', correo)], limit=1)
                mail_out = self.env['ir.mail_server'].search([('sequence', '=', 1)])
                if mail_out_temp:
                    email_from_priority = mail_out_temp.sequence
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 2})
                    mail_out_temp.write({'sequence': 1})
            for record in invoices:
                if record.invoice_date_due:
                    entered_date = record.invoice_date_due
                    entered_date = entered_date
                    a = entered_date - timedelta(days=int(param.sudo().get_param('qty_days_supplier')))
                    if fecha_act == a:
                        temp_id.send_mail(int(record.id), True)
            if temp_id.email_from:
                if mail_out_temp:
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 1})
                    mail_out_temp.write({'sequence': email_from_priority})

    @api.model
    def invoice_supplier_due(self):
        param = self.env['ir.config_parameter']
        email_due_today = bool(param.sudo().get_param('email_due_today_supplier'))
        if email_due_today:
            invoices = self.env['account.move'].search(
                [('state', '=', 'posted'), ('move_type', '=', 'out_invoice')])
            temp_id = self.env.ref('proandsys_dte_14.email_template_invoice_before_supplier')
            fecha_act = date.today()
            mail_out_temp = self.env['ir.mail_server'].search([])
            mail_out = self.env['ir.mail_server'].search([])
            email_from_priority = False
            if temp_id.email_from:
                st_mail = temp_id.email_from.find("<") + 1
                end_mail = temp_id.email_from.find(">")
                correo = temp_id.email_from[st_mail:end_mail]
                mail_out_temp = self.env['ir.mail_server'].search([('smtp_user', '=', correo)], limit=1)
                mail_out = self.env['ir.mail_server'].search([('sequence', '=', 1)])
                if mail_out_temp:
                    email_from_priority = mail_out_temp.sequence
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 2})
                    mail_out_temp.write({'sequence': 1})
            for record in invoices:
                if record.invoice_date_due:
                    entered_date = record.invoice_date_due
                    entered_date_invoice = record.invoice_date
                    entered_date = entered_date
                    entered_date_invoice = entered_date_invoice
                    b = entered_date
                    a = entered_date_invoice
                    if fecha_act == b or fecha_act > b:
                        temp_id.send_mail(record.id, True)
            if temp_id.email_from:
                if mail_out_temp:
                    if mail_out:
                        for x in mail_out:
                            x.write({'sequence': 1})
                    mail_out_temp.write({'sequence': email_from_priority})
    

class AccountMoveLineDte(models.Model):
    _inherit = 'account.move.line'

    def default_ind(self):
        res = '7'
        if 'type_id' in self._context:
            type_obj = self.env['l10n_latam.document.type'].browse(self._context['type_id'])
            if type_obj:
                if type_obj.code in ['1', '34', '38', '41']:
                    res = '1'
        return res

    ind_exencion = fields.Selection([('1', 'No afecto o exento de IVA'), \
                                     ('2', 'Producto o servicio no facturable'), \
                                     ('3', 'Garantia de deposito por envases'), \
                                     ('4', 'Item no venta'), ('5', 'Item a rebaja'), \
                                     ('6', 'Producto o servicio no facturable negativo'), \
                                     ('7', 'No aplica')], string='Indicador De Exencion', default=default_ind)
    
    
class AccountMoveReversalDte(models.TransientModel):
    _inherit = "account.move.reversal"
    
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Document Type', domain="[('code', 'in', ['60', '61'])]", readonly=False)

    @api.depends('move_ids')
    def _compute_document_type(self):
        self.l10n_latam_available_document_type_ids = False
        self.l10n_latam_document_type_id = False
        self.l10n_latam_use_documents = False
        for record in self:
            if len(record.move_ids) > 1:
                move_ids_use_document = record.move_ids._origin.filtered(lambda move: move.l10n_latam_use_documents)
                if move_ids_use_document:
                    raise UserError(_('You can only reverse documents with legal invoicing documents from Latin America one at a time.\nProblematic documents: %s') % ", ".join(move_ids_use_document.mapped('name')))
            else:
                record.l10n_latam_use_documents = record.move_ids.journal_id.l10n_latam_use_documents

            if record.l10n_latam_use_documents:
                refund = record.env['account.move'].new({
                    'move_type': record._reverse_type_map(record.move_ids.move_type),
                    'journal_id': record.move_ids.journal_id.id,
                    'partner_id': record.move_ids.partner_id.id,
                    'company_id': record.move_ids.company_id.id,
                })
                #record.l10n_latam_document_type_id = refund.l10n_latam_document_type_id
                record.l10n_latam_available_document_type_ids = refund.l10n_latam_available_document_type_ids

    def _prepare_default_reversal(self, move):
        """ Set the default document type and number in the new revsersal move taking into account the ones selected in
        the wizard """
        res = super()._prepare_default_reversal(move)
        dte = False
        if self.l10n_latam_document_type_id.code in ['60']:
            dte = False
        if self.l10n_latam_document_type_id.code in ['61']:
            dte = True
        res.update({
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': self.l10n_latam_document_number,
            'dte': dte,
        })
        return res