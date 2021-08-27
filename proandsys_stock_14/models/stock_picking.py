# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, exceptions, _
from odoo import SUPERUSER_ID
from odoo import netsvc
from odoo.tools import float_compare
from collections import OrderedDict
from datetime import datetime, time, date, timedelta
from ..tools.api import factual
import time, math, os, base64
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

import logging

logger = logging.getLogger(__name__)


class StockMoveExtDte(models.Model):
    _inherit = 'stock.move'

    @api.depends('quantity_done')
    def _compute_amount(self):
        for line in self:
            if line.sale_line_id:
                price = line.sale_line_id.price_unit * (1 - (line.sale_line_id.discount or 0.0) / 100.0)
                price_subtotal = price * line.quantity_done
                price_tax = price_subtotal * (line.sale_line_id.tax_id[0].amount/100)
                price_total = price_subtotal + price_tax
                line.update({
                    'price_sale': line.sale_line_id.price_unit,
                    'discount': line.sale_line_id.discount,
                    'price_tax': price_tax,
                    'price_total': price_total,
                    'price_subtotal': price_subtotal,
                })
            else:
                return 0

    sale_id = fields.Many2one(related='picking_id.sale_id', store=True, string='Pedido de Venta')
    price_sale = fields.Float('Precio Venta', required=True, digits=dp.get_precision('Product Price'), default=0.0,
                              readonly=False)
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Impuesto', readonly=True, store=True)
    price_total = fields.Float(compute='_compute_amount', string='Total', readonly=True, store=True)
    tax_id = fields.Many2many('account.tax', string='Impuestos',
                              domain=['|', ('active', '=', False), ('active', '=', True)])
    discount = fields.Float(string='Descuento (%)', digits=dp.get_precision('Discount'))


class StockPickingExtDte(models.Model):
    _inherit = 'stock.picking'
    
    @api.depends('move_ids_without_package.price_total')
    def amount_all_imp(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.move_ids_without_package:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed_imp': order.currency_id.round(amount_untaxed),
                'amount_tax_imp': order.currency_id.round(amount_tax),
                'amount_total_imp': order.currency_id.round(amount_untaxed + amount_tax),
            })
        return

    @api.constrains('sale_id')
    def set_references_sale(self):
        ref = self.env['l10n_cl_dte.reference']
        for x in self:
            x.write({'dte': True})
            for record in x.sale_id.reference_lines:
                item = ref.search([('picking_id', '=', x.id), ('ref_folio', '=', record.ref_folio),
                                   ('tpo_doc_ref', '=', record.tpo_doc_ref.id)], limit=1)
                if not item:
                    val = {
                        'tpo_doc_ref': record.tpo_doc_ref.id,
                        'ref_folio': record.ref_folio,
                        'ref_date': record.ref_date,
                        'picking_id': x.id
                    }
                    ref.create(val)
    
    amount_untaxed_imp = fields.Float(string='Subtotal', store=True, readonly=True, compute='amount_all_imp')
    amount_tax_imp = fields.Float(string='Impuesto', store=True, readonly=True, compute='amount_all_imp')
    amount_total_imp = fields.Float(string='Total', store=True, readonly=True, compute='amount_all_imp')
    
    sale_id = fields.Many2one('sale.order', "Presupuesto")
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                  default=lambda self: self.env.user.company_id.currency_id)
    internal_number = fields.Char('Numero interno', readonly=True, copy=False)
    dte_status = fields.Selection([('0', 'Fallo'), ('1', 'Aceptada')], 'Estado Factual', copy=False)
    dte_track = fields.Char('Track Dte', size=60, copy=False)
    sii_track_id = fields.Char('SII Track Id', size=60, copy=False)
    pdf_img = fields.Binary('PDF Ted Img', copy=False)
    ted_xml = fields.Text('TED',
                          copy=False)
    failed_text = fields.Text('Razón del fracaso', copy=False)
    sii_failed_text = fields.Text('SII Razón del fracaso', copy=False)
    dte_send = fields.Boolean('Enviar DTE', copy=False)
    dte = fields.Boolean('Es un documento DTE?')
    journal_id = fields.Many2one('account.journal', 'Diario', domain="[('code','=','STJ')]")
    reception_ack = fields.Boolean('Recepción Ack', default=False, copy=False)
    reception_ack_text = fields.Text('Texto Recepción Ack', copy=False)
    comercial_ack = fields.Boolean('Comercial Ack', default=False, copy=False)
    comercial_ack_text = fields.Text('Texto Comercial Ack', copy=False)
    ref_ready = fields.Boolean('Referencias Listas', copy=False)
    reference_lines = fields.One2many('l10n_cl_dte.reference', 'picking_id', string='Lineas de Referencias', copy=False)
    get_data = fields.Boolean('Obtener Data', copy=False)
    fecha_guia = fields.Date('Fecha Guia')
    referencia = fields.Char('Referencia Recepcion')
    rut_transpor = fields.Char('Rut Transportista')
    patente_vehic = fields.Char('Patente Vehiculo')
    anulada = fields.Char('Guia Anulada')
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Tipo de documento', ondelete='cascade',
                                                  domain="[('code', 'in', ['52'])]", readonly=False)
    
    ind_traslado = fields.Selection([('1', 'Operacion Constituye Venta'), \
                                     ('2', 'Ventas por Efectuar'), \
                                     ('3', 'Consignaciones'), \
                                     ('4', 'Entrega Gratuita'), \
                                     ('5', 'Traslado Interno No Constituye Venta'), \
                                     ('6', 'Otros Traslados no Venta'), \
                                     ('7', 'Guia de Devolucion'), \
                                     ('8', 'Traslado para Exportacion. (No Venta)'), \
                                     ('9', 'Venta para Exportacion')], 'Indicador de Traslado', default='1')
    state_dte = fields.Selection([('dte_none', 'No Aplica DTE'), ('dte_waiting', 'Por Aprobar DTE'), \
                                  ('dte_failed', 'DTE Fallido'), ('dte_acepted', 'DTE Aceptado'), \
                                  ('dte_cancel', 'DTE Cancelado')], \
                                 string='Estado DTE', readonly=True, default='dte_none', copy=False)
    
    def get_dte_info(self):
        for picking in self:
            res = factual.get_dte_info(picking.company_id.dte_url, picking.company_id.partner_id.vat, \
                                       picking.l10n_latam_document_type_id.code, str(picking.name), \
                                       picking.company_id.dte_user, picking.company_id.dte_pass)
            if res['Status'] and res['Status'] == 1:
                data = {
                    'ted_xml': res['TedXml'],
                    'pdf_img': res['TedImageBase64'],
                    'get_data': True,
                    'failed_text': None,
                    'sii_failed_text': None,
                    'dte_track': res['TrackId'],
                }
                self.write([picking.id], data)
            else:
                raise exceptions.Warning(res['Description'])
        return True
    
    def get_acks(self):
        for picking in self:
            status = factual.get_status(picking.company_id.dte_url, picking.dte_track, picking.company_id.dte_user, \
                                        picking.company_id.dte_pass)
            if status['Approved']:
                if status['CommertialAck']:
                    if status['CommertialAckStatus'] == 0:
                        self.write([picking.id], {'comercial_ack': True})
                    elif status['CommertialAckStatus'] == 1:
                        self.write([picking.id], {'comercial_ack': True, \
                                                  'comercial_ack_text': status['CommertialAckInfo']})
                    else:
                        self.write([picking.id], \
                                   {'comercial_ack_text': status['CommertialAckInfo']})
                if status['ReceptionAck']:
                    self.write([picking.id], {'reception_ack': True})
                if status['ReceptionAckInfo']:
                    self.write([picking.id], {'reception_ack_text': status['ReceptionAckInfo']})
        return True
    
    def send_dte(self):
        dte = OrderedDict()
        codes = OrderedDict()
        detail = OrderedDict()
        discount = OrderedDict()
        reference = OrderedDict()
        dte_detail = []
        dte_discount = []
        dte_reference = []

        for picking in self:
            if picking.get_data:
                self.write({'failed_text': None, 'sii_failed_text': None})
                return True
            if not picking.move_ids_without_package:
                raise exceptions.Warning('Debe existir al menos una linea en la guía de despacho')
            if not picking.ref_ready:
                raise exceptions.Warning('Debe marcar como listas las referencias del documento.')
            if picking.company_id.ind_folios == '2' and picking.dte:
                if not picking.internal_number:
                    f_id = self.env['l10n_cl_dte.folio_history'].search(
                        [('company_id', '=', picking.company_id.id), ('active', '=', True),
                         ('type_id', '=', picking.l10n_latam_document_type_id.id)])
                    if f_id:
                        # FIXME: quisas sea bueno en esta parte crear un metodo en el folio_history para manejar los folios
                        f_obj = f_id[0]
                        if (f_obj.end_folio - f_obj.next_value) < 0:
                            raise exceptions.Warning('Ya no tiene mas folios para emitir documentos de este tipo.')
                    else:
                        raise exceptions.Warning(
                            'No se han encontrado registros de folios activos para este diario. Favor verificar')
            cont = 1
            for line in picking.reference_lines:
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
                cont += 1
                dte_reference.append(reference.copy())

            # Detalles
            cont = 1
            cont_disc = 1
            for line in picking.move_lines:
                if line.price_sale > 0:
                    codes['TpoCodigo'] = 'EAN' if line.product_id.barcode else 'Interna'
                    codes['VlrCodigo'] = line.product_id.barcode or line.product_id.default_code or ''
                    dte_codes = [codes.copy()]

                    detail['NroLinDet'] = cont
                    detail['CdgItems'] = dte_codes
                    detail['NmbItem'] = line.product_id and line.product_id.name[:80] or line.name.replace('\n', ' ')[:80]
                    detail['DscItem'] = line.product_id.name.replace('\n', '')
                    detail['QtyItem'] = round(line.product_uom_qty, 3)
                    detail['Subcantidades'] = []
                    detail['UnmdItem'] = line.product_uom.name[:4]
                    detail['PrcItem'] = round(line.price_sale, 3)
                    detail['MontoItem'] = int(round(line.price_subtotal, 0))
                    cont += 1
                    dte_detail.append(detail.copy())
                else:
                    dte_discount.append({
                        'NroLinDR': cont_disc,
                        'TpoMov': 'D',
                        'TpoValor': '$',
                        'ValorDR': -line.price_subtotal
                    })
                    cont_disc += 1
            discount['DscRcgGlobal'] = dte_discount
            dte['TipoDTE'] = picking.l10n_latam_document_type_id.code
            if picking.company_id.ind_folios == '2' and picking.dte:
                dte['Folio'] = self.env['l10n_cl_dte.folio_history'].folio_consume(
                f_id[0].id) if not picking.internal_number else picking.internal_number
            else:
                raise exceptions.Warning('Debe estar transferido el movimiento, no se encontro el nombre')
            if picking.fecha_guia:
                dte['FchEmis'] = picking.fecha_guia
            else:
                raise exceptions.Warning('No exite fecha de emision')
            dte['IndTraslado'] = int(picking.ind_traslado)

            if picking.company_id.partner_id.vat:
                dte['RUTEmisor'] = picking.company_id.partner_id.vat
            else:
                raise exceptions.Warning('Configure su Rut en el menu de companias para emitir documentos electronicos')
            if picking.company_id.partner_id.name:
                dte['RznSocEmisor'] = picking.company_id.partner_id.name
            else:
                raise exceptions.Warning('Configure su Nombre en el menu de companias')
            if picking.company_id.partner_id.giro:
                dte['GiroEmis'] = picking.company_id.partner_id.giro[:80]
            else:
                raise exceptions.Warning('Configure su Giro en el menu de companias')
            if picking.company_id.partner_id.economic_act_ids:
                dte['Acteco'] = int(picking.company_id.partner_id.economic_act_ids[0].code)
            else:
                raise exceptions.Warning('No se puede crear una guia de despacho sin actividad economica')
            if picking.company_id.partner_id.phone and picking.company_id.partner_id.mobile:
                dte['Telefono'] = picking.company_id.partner_id.phone + '-' + picking.company_id.partner_id.mobile
            elif picking.company_id.partner_id.phone:
                dte['Telefono'] = picking.company_id.partner_id.phone
            elif picking.company_id.partner_id.mobile:
                dte['Telefono'] = picking.company_id.partner_id.mobile
            else:
                raise exceptions.Warning('Debe ingresar un numero telefonico para su empresa')

            if picking.company_id.partner_id.street and picking.company_id.partner_id.street2:
                dte['DirOrigen'] = '%s %s' % (
                    picking.company_id.partner_id.street, picking.company_id.partner_id.street2)
            elif picking.company_id.partner_id.street:
                dte['DirOrigen'] = picking.company_id.partner_id.street
            elif picking.company_id.partner_id.street2:
                dte['DirOrigen'] = picking.company_id.partner_id.street2
            else:
                raise exceptions.Warning('You must set a street for your company.')
            if picking.company_id.partner_id.state_id:
                dte['CmnaOrigen'] = picking.company_id.partner_id.state_id.name
            else:
                raise exceptions.Warning('Configure su comuna en el menu de companias')
            if picking.company_id.partner_id.city:
                dte['CiudadOrigen'] = picking.company_id.partner_id.city
            else:
                raise exceptions.Warning('Configure su ciudad en el menu de companias')

            if picking.partner_id.parent_id.vat:
                dte['RUTRecep'] = picking.partner_id.parent_id.vat
            elif picking.partner_id.vat:
                dte['RUTRecep'] = picking.partner_id.vat
            elif picking.partner_id.vat:
                raise exceptions.Warning('Configure su Rut en el menu de clientes para emitir documentos electronicos')
            if picking.partner_id.ref:
                dte['CdgIntRecep'] = picking.partner_id.ref
            if picking.partner_id.parent_id.name:
                dte['RznSocRecep'] = picking.partner_id.parent_id.name[:100]
            elif picking.partner_id.name:
                dte['RznSocRecep'] = picking.partner_id.name[:100]
            else:
                raise exceptions.Warning('Configure el Nombre del cliente seleccionado.')
            if picking.partner_id.parent_id.giro:
                dte['GiroRecep'] = picking.partner_id.parent_id.giro[:40]
            elif picking.partner_id.giro:
                dte['GiroRecep'] = picking.partner_id.giro[:40]
            else:
                raise exceptions.Warning('Configure the el Giro del cliente seleccionado')
            if picking.partner_id.street and picking.partner_id.street2:
                dte['DirRecep'] = '%s %s' % (picking.partner_id.street, picking.partner_id.street2)
            elif picking.partner_id.street:
                dte['DirRecep'] = picking.partner_id.street[:70]
            elif picking.partner_id.street2:
                dte['DirRecep'] = picking.partner_id.street2[:70]
            else:
                raise exceptions.Warning('You must set a street for the selected partner.')
            if picking.partner_id.state_id:
                dte['CmnaRecep'] = picking.partner_id.state_id.name[:70]
            else:
                raise exceptions.Warning('Configure la comuna en el menu de clientes')
            if picking.partner_id.city:
                dte['CiudadRecep'] = picking.partner_id.city[:70]
            else:
                raise exceptions.Warning('Configure su ciudad en el menu de clientes')

            if picking.partner_id.street and picking.partner_id.street2:
                dte['DirDest'] = '%s %s' % (picking.partner_id.street, picking.partner_id.street2)
            elif picking.partner_id.street:
                dte['DirDest'] = picking.partner_id.street[:70]
            elif picking.partner_id.street2:
                dte['DirDest'] = picking.partner_id.street2[:70]
            else:
                raise exceptions.Warning('You must set a street for the selected partner.')
            if picking.partner_id.state_id:
                dte['CmnaDest'] = picking.partner_id.state_id.name[:70]
            else:
                raise exceptions.Warning('Configure su comuna en el menu de companias')
            if picking.partner_id.city:
                dte['CiudadDest'] = picking.partner_id.city[:70]
            else:
                raise exceptions.Warning('Configure su ciudad en el menu de companias')

            dte['MntNeto'] = int(round(picking.amount_untaxed_imp, 0))
            dte['MntExe'] = 0
            dte['IVA'] = int(round(picking.amount_tax_imp, 0))

            dte['TasaIVA'] = 19.00
            dte['MntTotal'] = int(round(picking.amount_total_imp, 0))

            dte['Referencias'] = dte_reference
            dte['Detalles'] = dte_detail
            dte['DescuentosGlobales'] = discount

            dte['Extensiones'] = {'Web': picking.company_id.partner_id.website}
            if picking.note:
                dte['Extensiones'].update({'Notas': picking.note})

            if not dte['FchEmis']:
                del dte['FchEmis']
                raise exceptions.Warning('Se debe especificar una Fecha de Emision para la Guia.')

            # Se envia la data a factual.
            res = factual.send_dte(picking.company_id.dte_url, dte, picking.company_id.dte_user, picking.company_id.dte_pass)

            # Se selecciona el procesimiento dependiendo de la respuesta satisfactoria o rechazada del documento.
            if not res['Status'] or res['Status'] != 1:
                if res['ValidationErrors'] and res['Description']:
                    error = """%s \n%s""" % (res['ValidationErrors'][0], res['Description'])
                elif res['ValidationErrors']:
                    error = """%s""" % (res['ValidationErrors'][0])
                elif res['Description']:
                    error = """%s""" % (res['Description'])
                else:
                    error = ''

                self.write({
                    'internal_number': dte['Folio'],
                    'failed_text': error,
                    'state_dte': 'dte_failed'})
            else:
                data = {
                    'dte_send': True,
                    'ted_xml': res['TedXml'],
                    'pdf_img': res['TedImageBase64'],
                    'dte_track': res['TrackId'],
                    'internal_number': dte['Folio'],
                    'failed_text': None,
                    'sii_failed_text': None,
                    'state_dte': 'dte_acepted',
                }
                self.write(data)
                ref = {
                    'tpo_doc_ref': self.l10n_latam_document_type_id.id,
                    'ref_folio': self.internal_number,
                    'ref_date': self.scheduled_date,
                    'sale_id': self.sale_id.id,
                }
                self.env['l10n_cl_dte.reference'].create(ref)
        return True
    
    def get_validation(self):
        picking = self
        res = factual.get_status(picking.company_id.dte_url, picking.dte_track, picking.company_id.dte_user, \
                                 picking.company_id.dte_pass)
        try:
            if res['Approved']:
                self.write({'sii_failed_text': None, 'failed_text': None, 'dte_status': '1', \
                            'sii_track_id': res['SiiTrackId']})
            else:
                self.write({'sii_failed_text': res['Comments'], 'dte_status': '0', 'dte_send': False, \
                            'sii_track_id': res['SiiTrackId']})
        except:
            raise exceptions.Warning(str(res['Description']))
        return True
    
    def anular_dte(self):
        for record in self:
            if record.state in ['cancel']:
                record.anulada = record.internal_number
                record.internal_number = ''
                record.state_dte = 'dte_cancel'
            else:
                raise exceptions.Warning('Debe cancelar la entrega para anular la guia')
