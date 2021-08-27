# -*- coding: utf-8 -*-
from ..tools.api import factual
from collections import OrderedDict
from odoo import models, fields, api, exceptions
import base64
import logging
from bs4 import BeautifulSoup
_logger = logging.getLogger(__name__)


class DtePaymentType(models.Model):
    _name = 'l10n_cl_dte.payment_type'
    _descripcion = 'Tipo de Pago'
    _order = 'code'

    name = fields.Char('Nombre', size=64, required=True)  # Nombre del tipo de pago
    internal_code = fields.Char('Codígo Interno', size=10)  # Codigo interno de la empresa
    code = fields.Char('Codígo SII', size=4, required=True)  # nombre del Tipo de pago como OT


class FolioHistoryDte(models.Model):
    _name = 'l10n_cl_dte.folio_history'
    _description = 'Historial de Folio por Tipo de Documento'

    type_id = fields.Many2one('l10n_latam.document.type', 'Tipo de documento', ondelete='cascade')
    sequence_id = fields.Many2one('ir.sequence', 'Secuencia Asociada')
    begin_folio = fields.Integer('Folio Inicial')
    end_folio = fields.Integer('Folio Final')
    next_value = fields.Integer('Folio Siguiente')
    file_code = fields.Char('Codígo')
    public_key = fields.Text('Clave Pública')
    private_key = fields.Text('Clave Privada')
    xml = fields.Text('XML Original')
    caf = fields.Text('XML CAF')
    file = fields.Binary('Archivo')
    active = fields.Boolean('Activo')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)

    def _get_journals(self):
        folio_ids = []
        for journal in self:
            for id in self.env['l10n_cl_dte.folio_history'].search([('journal_id', '=', journal.id)]):
                folio_ids.append(id)
        return folio_ids

    def onchange_journal(self, journal_id, file_code):
        if journal_id and file_code:
            j_obj = self.env['account.journal'].browse(journal_id)
            if j_obj.l10n_latam_document_type_id.code != file_code:
                value = {
                    'journal_id': self.journal_id.id
                }
                warning = {
                    'title': 'Codigo de Diario Incorrecto!',
                    'message': 'El codigo del diario no corresponde con el importado del archivo de SII.'
                }
                return {'warning': warning, 'value': value}
            else:
                return {}
        else:
            return {}

    def folio_consume(self, folio_id):
        """Retorna el folio actual para el id de diario y adelanta el contador de folios en uno,
         producciendo que los folios avancen """

        folio_obj = self.env['l10n_cl_dte.folio_history'].browse(folio_id)
        f_actual = folio_obj.next_value
        folio_obj.next_value = f_actual + 1
        return f_actual

    @api.model
    def create(self, vals):
        data = {}
        res = super(FolioHistoryDte, self).create(vals)
        f_obj = res
        if 'file' in vals:
            data['cafBase64'] = vals['file']
            status = factual.set_caf(url=f_obj.company_id.dte_url, data=data, user=f_obj.company_id.dte_user, \
                                     passwd=f_obj.company_id.dte_pass)

            if not status['Status']:
                raise exceptions.Warning( \
                    'Sus Folios no ha sido cargados correctamente ' + \
                    'El error es el siguiente:' + status['Description'].decode('ascii'))
        return res

    def write(self, vals):
        data = {}
        res = super(FolioHistoryDte, self).write(vals)
        if 'file' in vals:
            for f_obj in self:
                data['cafBase64'] = vals['file']
                status = factual.set_caf(url=f_obj.company_id.dte_url, data=data, user=f_obj.company_id.dte_user, \
                                         passwd=f_obj.company_id.dte_pass)
                if not status['Status']:
                    raise exceptions.Warning( \
                        'Sus Folios no ha sido cargados correctamente ' + \
                        'El error es el siguiente:' + status['Description'])
        return res

    def _check_unique(self):
        if self.search(
                [('company_id', '=', self.company_id.id), ('type_id', '=', self.type_id.id), ('active', '=', True),
                 ('id', '!=', self.id)]) and self.active:
            return False
        return True

    _constraints = [
        (_check_unique, 'Solo se puede tener un folio activo por tipo de documento y compañia.',
         ['type_id', 'company_id', 'active'])
    ]


class TipoDespachoDte(models.Model):
    _name = 'l10n_cl_dte.tipo_despacho'
    _description = 'Tipo Despacho'

    name = fields.Char('Nombre', size=64, required=True)
    code = fields.Integer('Codígo', required=True)
    description = fields.Text('Descripción')


class TipoTrasladoDte(models.Model):
    _name = 'l10n_cl_dte.tipo_traslado'
    _description = 'Tipo Traslado'

    name = fields.Char('Name', size=64, required=True)
    code = fields.Integer('Code', required=True)


class TipoImpresionGuiaDte(models.Model):
    _name = 'l10n_cl_dte.tipo_imp_guia'
    _description = 'Tipo Impresion Guia'

    name = fields.Char('Nombre', size=64, required=True)
    code = fields.Char('Codígo', size=1, required=True)


class IndicadorServicioDte(models.Model):
    _name = 'l10n_cl_dte.ind_servicio'
    _description = 'Indicador Servicio'

    name = fields.Char('Nombre', size=64, required=True)
    code = fields.Integer('Codígo', required=True)
    description = fields.Text('Descripción')


class FormaPagoDte(models.Model):
    _name = 'l10n_cl_dte.forma_pago'
    _description = 'Forma Pago'

    name = fields.Char('Nombre', size=64, required=True)
    code = fields.Char('Codígo', size=1, required=True)


class CodigoTrasladoDte(models.Model):
    _name = 'l10n_cl_dte.codigo_traslado'
    _description = 'Codigo Emisor Traslado Excepcional'

    name = fields.Char('Nombre', size=64, required=True)
    code = fields.Char('Codígo', size=1, required=True)
    description = fields.Text('Descripción')


class SucursalesDte(models.Model):
    _name = 'l10n_cl_dte.sucursal'
    _description = 'Mantenedor de Sucursales'

    name = fields.Char('Nombre', size=64, required=True)
    code = fields.Char('Codígo', size=1, required=True)
    description = fields.Text('Descripción')


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


class LibrosElectronicos(models.Model):
    _name = 'l10n_cl_dte.electronic_books'
    _description = 'Mantenedor de Libros Electronicos'

    name = fields.Char('Nombre', size=64)
    type = fields.Selection(
        [('96', 'Libro de Boletas'), ('97', 'Libro Guias de Despacho'), ('98', 'Libro de Ventas'), ('99', 'Libro de Compras')],
        'Type', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True)
    xml = fields.Text('XML')
    state = fields.Char('Estatus', size=60, required=True)
    sii_track_id = fields.Char('SII ID Track', size=60)
    track_id = fields.Char('ID Track', size=60)
    failed_text = fields.Text('Error')

    def get_validation_book(self):
        for book in self:
            res = factual.status_book(book.company_id.dte_url, book.track_id, user=book.company_id.dte_user, passwd=book.company_id.dte_pass)
            if res['Status']:
                self.write({'state': 'Approved' if res['Approved'] else 'Waiting Validation'})
        return True

    def get_xml_book(self):
        for book in self:
            if not book.track_id:
                raise ('Error!', \
                       'No se puede validar un libro con fallos, se debe eliminar el libro actual y volver a enviar por el wizard.')
            track_id = None
            sii_track = None
            sii_status = None
            failed_text = None
            book_content = None

            res = factual.status_book(book.company_id.dte_url, book.track_id, user=book.company_id.dte_user, passwd=book.company_id.dte_pass)
            if res['Status']:
                sii_track = res['SiiTrackId']
                sii_status = 'Approved' if res['Approved'] else 'Waiting Validation'
                xml = factual.get_xml_book(book.company_id.dte_url, book.track_id, user=book.company_id.dte_user,
                                           passwd=book.company_id.dte_pass)
                if xml['Status']:
                    book_content = (base64.decodestring(xml['BookContent'])).decode('iso-8859-1')
                    track_id = xml['TrackId']
                else:
                    failed_text = res['Description']
            else:
                if res['ValidationErrors'] and res['Description']:
                    failed_text = """%s \n%s""" % (res['ValidationErrors'][0], res['Description'])
                elif res['ValidationErrors']:
                    failed_text = """%s""" % (res['ValidationErrors'][0])
                elif res['Description']:
                    failed_text = """%s""" % (res['Description'])
                else:
                    failed_text = ''

            self.write(
                {'xml': book_content, 'state': sii_status, 'sii_track_id': sii_track, 'failed_text': failed_text})
        return True


class Subcantidades(models.Model):
    _name = 'l10n_cl_dte.subqty_xml'
    _rec_name = 'sub_cod'

    sub_qty = fields.Char('Subcantidad Distribuida', size=18)
    sub_cod = fields.Char('Codigo Subcantidad', size=35)
    sub_type = fields.Char('Tipo Codigo Subcantidad', size=10)
    line_id = fields.Many2one('l10n_cl_dte.document_xml_lines', 'Linea')


class CodigoItem(models.Model):
    _name = 'l10n_cl_dte.code_items_xml'
    _rec_name = 'tipo_codigo'

    tipo_codigo = fields.Char('Tipo Código', size=30)
    valor_codigo = fields.Char('Valor Código', size=30)
    line_id = fields.Many2one('l10n_cl_dte.document_xml_lines', 'Linea')


class DocumentXml(models.Model):
    _name = 'l10n_cl_dte.document_xml'
    _rec_name = 'folio'

    def ordena_dict_factura(self, data, data_invoice):
        soup = BeautifulSoup(data)
        if soup.find('acteco'): data_invoice['acteco'] = soup.find('acteco').string
        if soup.find('bcopago'): data_invoice['banco_pago'] = soup.find('bcopago').string
        if soup.find('cdgintrecep'): data_invoice['codigo_int_receptor'] = soup.find('cdgintrecep').string
        if soup.find('cdgsiisucur'): data_invoice['codigo_sucursal_sii'] = soup.find('cdgsiisucur').string
        if soup.find('cdgvendedor'): data_invoice['codigo_vendedor'] = soup.find('cdgvendedor').string
        if soup.find('ciudadorigen'): data_invoice['ciudad_origen'] = soup.find('ciudadorigen').string
        if soup.find('ciudadpostal'): data_invoice['ciudad_postal'] = soup.find('ciudadpostal').string
        if soup.find('ciudadrecep'): data_invoice['ciudad_receptor'] = soup.find('ciudadrecep').string
        if soup.find('cmnacrigen'): data_invoice['comuna_origen'] = soup.find('cmnacrigen').string
        if soup.find('cmnapostal'): data_invoice['comuna_postal'] = soup.find('cmnapostal').string
        if soup.find('cmnarecep'): data_invoice['comuna_receptor'] = soup.find('cmnarecep').string
        if soup.find('comisiones'): data_invoice['comisiones'] = soup.find('comisiones').string
        if soup.find('contacto'): data_invoice['contacto'] = soup.find('contacto').string
        if soup.find('correoemisor'): data_invoice['correo_emisor'] = soup.find('correoemisor').string
        if soup.find('correorecep'): data_invoice['correo_receptor'] = soup.find('correorecep').string
        if soup.find('descuentosglobales'): data_invoice['dctos_globales'] = soup.find('descuentosglobales').string
        if soup.find('dirorigen'): data_invoice['direccion_origen'] = soup.find('dirorigen').string
        if soup.find('dirpostal'): data_invoice['direccion_postal'] = soup.find('dirpostal').string
        if soup.find('dirrecep'): data_invoice['direccion_receptor'] = soup.find('dirrecep').string
        if soup.find('extranjeronacionalidad'): data_invoice['extranjero_nacionalidad'] = soup.find('extranjeronacionalidad').string
        if soup.find('extranjeronunmid'): data_invoice['extranjero_num_id'] = soup.find('extranjeronunmid').string
        if soup.find('fchcancel'): data_invoice['date_cancel'] = soup.find('fchcancel').string
        if soup.find('fchemis'): data_invoice['date'] = soup.find('fchemis').string
        if soup.find('fchvenc'): data_invoice['date_due'] = soup.find('fchvenc').string
        if soup.find('fmapagexp'): data_invoice['forma_pago_exp'] = soup.find('fmapagexp').string
        if soup.find('fmapago'): data_invoice['forma_pago'] = soup.find('fmapago').string
        if soup.find('fmapago'):
            if soup.find('fmapago').string == '1':
                data_invoice['comercial_state'] = '1'
        if soup.find('folio'): data_invoice['folio'] = soup.find('folio').string
        if soup.find('giroemis'): data_invoice['giro_emisor'] = soup.find('giroemis').string
        if soup.find('girorecep'): data_invoice['giro_receptor'] = soup.find('girorecep').string
        if soup.find('iva'): data_invoice['IVA'] = soup.find('iva').string
        if soup.find('ivaprop'): data_invoice['iva_prop'] = soup.find('ivaprop').string
        if soup.find('ivaterc'): data_invoice['iva_terc'] = soup.find('ivaterc').string
        if soup.find('indmntneto'): data_invoice['ind_monto_neto'] = soup.find('indmntneto').string
        if soup.find('indnorebaja'): data_invoice['ind_no_rebaja'] = soup.find('indnorebaja').string
        if soup.find('indservicio'): data_invoice['ind_servicio'] = soup.find('indservicio').string
        if soup.find('indtraslado'): data_invoice['ind_traslado'] = soup.find('indtraslado').string
        if soup.find('integrationpointid'): data_invoice['integration_point_id'] = soup.find('integrationpointid').string
        if soup.find('internalnumber'): data_invoice['int_number'] = soup.find('internalnumber').string
        if soup.find('mediopago'): data_invoice['medio_pago'] = soup.find('mediopago').string
        data_invoice['monto_bruto'] = soup.find('mntbruto').string if soup.find('mntbruto') else 0
        data_invoice['monto_cancelar'] = soup.find('mntcancel').string if soup.find('mntcancel') else 0
        if soup.find('mntexe'): data_invoice['monto_exento'] = soup.find('mntexe').string
        if soup.find('mntneto'): data_invoice['monto_neto'] = soup.find('mntneto').string
        data_invoice['monto_pagos'] = soup.find('mntpagos').string if soup.find('mntpagos') else 0
        if soup.find('mnttotal'): data_invoice['monto_total'] = soup.find('mnttotal').string
        if soup.find('montoimp'): data_invoice['monto_imp'] = soup.find('montoimp').string
        data_invoice['monto_nf'] = soup.find('montonf').string if soup.find('montonf') else 0
        data_invoice['monto_periodo'] = soup.find('montoperiodo').string if soup.find('montoperiodo') else 0
        if soup.find('numctapago'): data_invoice['numero_cta_pago'] = soup.find('numctapago').string
        if soup.find('periododesde'): data_invoice['periodo_desde'] = soup.find('periododesde').string
        if soup.find('periodohasta'): data_invoice['periodo_hasta'] = soup.find('periodohasta').string
        if soup.find('rutemisor'): data_invoice['rut_emisor'] = soup.find('rutemisor').string
        if soup.find('rutmandante'): data_invoice['rut_mandante'] = soup.find('rutmandante').string
        if soup.find('rutrecep'): data_invoice['rut_receptor'] = soup.find('rutrecep').string
        if soup.find('rznsoc'): data_invoice['razon_social_emisor'] = soup.find('rznsoc').string
        if soup.find('rznsocrecep'): data_invoice['razon_social_receptor'] = soup.find('rznsocrecep').string
        if soup.find('saldoanterior'): data_invoice['saldo_anterior'] = soup.find('saldoanterior').string
        if soup.find('saldoinsol'): data_invoice['saldo_insol'] = soup.find('saldoinsol').string
        if soup.find('sucursal'): data_invoice['sucursal'] = soup.find('sucursal').string
        if soup.find('tasaiva'): data_invoice['tasa_iva'] = soup.find('tasaiva').string
        if soup.find('tasaimp'): data_invoice['tasa_imp'] = soup.find('tasaimp').string
        if soup.find('tedxml'): data_invoice['tedxml'] = soup.find('tedxml').string
        if soup.find('telefono'): data_invoice['telefono'] = soup.find('telefono').string
        if soup.find('termpagocdg'): data_invoice['cod_term_pago'] = soup.find('termpagocdg').string
        if soup.find('termpagodias'): data_invoice['dias_term_pago'] = soup.find('termpagodias').string
        if soup.find('termpagoglosa'): data_invoice['glosa_term_pago'] = soup.find('termpagoglosa').string
        if soup.find('tipodte'): data_invoice['tipo_dte'] = soup.find('tipodte').string
        if soup.find('tipodespacho'): data_invoice['tipo_despacho'] = soup.find('tipodespacho').string
        if soup.find('tipoimp'): data_invoice['tipo_impresion'] = soup.find('tipoimp').string
        if soup.find('totalperiodo'): data_invoice['total_periodo'] = soup.find('totalperiodo').string
        if soup.find('tpoctapago'): data_invoice['tipo_cta_pago'] = soup.find('tpoctapago').string
        if soup.find('tpomoneda'): data_invoice['tipo_moneda'] = soup.find('tpomoneda').string
        if soup.find('valcomexe'): data_invoice['valor_exento'] = soup.find('valcomexe').string
        if soup.find('valcomiva'): data_invoice['valor_iva'] = soup.find('valcomiva').string
        if soup.find('valcomneto'): data_invoice['valor_neto'] = soup.find('valcomneto').string
        if soup.find('vlrpagar'): data_invoice['valor_pagar'] = soup.find('vlrpagar').string
        if soup.find('rutemisor'):
            rc = soup.find('rutemisor').string
            d = rc[-2:]
            c = rc[-5:-2]
            b = rc[-8:-5]
            a = rc[:-8]
            conv_rut = a + '.' + b + '.' + c + d
            partner = self.env['res.partner'].search([('vat', '=', conv_rut)], limit=1)
            if partner:
                data_invoice['provider_id'] = partner.id
        return data_invoice

    def action_enviar_acuse(self):
        return {
            'binding_view_types': 'list',
            'view_mode': 'form',
            'res_model': 'send.ack.wizard',
            'view_id': self.env.ref('proandsys_dte_14.view_send_ack_dte_wizard_form').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
            },
        }

    @api.model
    def create_doc_webhook(self, data=None):
        data_invoice = {}
        data_invoice = self.ordena_dict_factura(data, data_invoice)
        invoice_id = self.create(data_invoice)
        soup = BeautifulSoup(data)
        for detalle in soup.find_all('detalle'):
            data_line = {}
            data_line['invoice_id'] = invoice_id.id

            if detalle.find('dscitem'): data_line['detalle'] = detalle.find('dscitem').string
            if detalle.find('montoitem'): data_line['precio_unitario'] = detalle.find('montoitem').string
            if detalle.find('nmbitem'): data_line['nmb_item'] = detalle.find('nmbitem').string
            if detalle.find('nrolindet'): data_line['n_lineas_detalle'] = detalle.find('nrolindet').string
            if detalle.find('prcitem'):
                data_line['prc'] = round(float(detalle.find('prcitem').string),0)
            else:
                if detalle.find('qtyitem'):
                    data_line['prc'] = round((float(detalle.find('montoitem').string) / float(detalle.find('qtyitem').string)),0)
                else:
                    data_line['prc'] = round((float(detalle.find('montoitem').string)),0)
            data_line['cantidad'] = detalle.find('qtyitem').string if detalle.find('qtyitem') else 1
            if detalle.find('qtyref'): data_line['cantidad_referencial'] = detalle.find('qtyref').string
            if detalle.find('unmditem'): data_line['unmd'] = detalle.find('unmditem').string
            line_id = self.env['l10n_cl_dte.document_xml_lines'].create(data_line)
            if detalle.find('cdgitem'):
                for code in detalle.find('cdgitem'):
                    code_line = {}
                    code_line['line_id'] = line_id.id

                    if code.find('tpocodigo'): code_line['tipo_codigo'] = code.find('tpocodigo')
                    if code.find('vlrcodigo'): code_line['valor_codigo'] = code.find('vlrcodigo')
                    self.env['l10n_cl_dte.code_items_xml'].create(code_line)

            # Subcantidades de los items
            if detalle.find('subcantidades'):
                for sub in detalle.find('subcantidades'):
                    sub_line = {}
                    sub_line['line_id'] = line_id.id

                    if sub.find('subqty'): sub_line['sub_qty'] = sub.find('subqty').string
                    if sub.find('subcod'): sub_line['sub_cod'] =  sub.find('subcod').string
                    if sub.find('tipcodsubqty'): sub_line['sub_type'] = sub.find('tipcodsubqty').string
                    self.env['l10n_cl_dte.subqty_xml'].create(sub_line)
        for ref in soup.find_all('referencia'):
            data_ref = {}
            data_ref['invoice_id'] = invoice_id.id
            if ref.find('nrolinref'): data_ref['numero_ref'] = ref.find('nrolinref').string
            if ref.find('tpodocref'): data_ref['tipo_doc_ref'] = ref.find('tpodocref').string
            if ref.find('folioref'): data_ref['folio_ref'] = ref.find('folioref').string
            if ref.find('fchref'): data_ref['fecha_ref'] = ref.find('fchref').string
            if ref.find('razonref'): data_ref['razon_ref'] = ref.find('razonref').string
            if ref.find('codref'): data_ref['codigo_ref'] = ref.find('codref').string
            self.env['l10n_cl_dte.document_xml_references'].create(data_ref)
        return True

    tipo_dte = fields.Char('Tipo DTE', size=3)
    folio = fields.Char('Folio', size=60)
    int_number = fields.Char('Número Interno', size=60)
    date = fields.Date('Fecha de Factura')
    date_due = fields.Date('Fecha de Vencimiento')
    date_account = fields.Date('Fecha Contable')
    date_cancel = fields.Date('Fecha de Cancelación')
    periodo_desde = fields.Char('Periodo Desde', size=10)
    periodo_hasta = fields.Char('Periodo Hasta', size=10)
    tipo_impresion = fields.Char('Tipo Impresión', size=10)
    rut_emisor = fields.Char('Rut Emisor', size=10)
    giro_emisor = fields.Char('Giro Emisor', size=300)
    acteco = fields.Char('Acteco', size=20)
    razon_social_emisor = fields.Char('Razón Social Emisor', size=300)
    comuna_origen = fields.Char('Comúna Origen', size=300)
    ciudad_origen = fields.Char('Ciudad Origen', size=300)
    direccion_origen = fields.Char('Dirección Origen', size=300)
    sucursal = fields.Char('Sucursal', size=300)
    codigo_sucursal_sii = fields.Char('Código SII', size=20)
    contacto = fields.Char('Contacto', size=300)
    telefono = fields.Char('Teléfono', size=50)
    direccion_postal = fields.Char('Dirección Postal', size=300)
    comuna_postal = fields.Char('Comúna Postal', size=300)
    ciudad_postal = fields.Char('Ciudad Postal', size=300)
    codigo_vendedor = fields.Char('Código Vendedor', size=20)
    codigo_int_receptor = fields.Char('Código Interno Receptor', size=50)
    rut_receptor = fields.Char('Rut Receptor', size=10)
    razon_social_receptor = fields.Char('Razón Social Receptor', size=300)
    giro_receptor = fields.Char('Giro Receptor', size=300)
    direccion_receptor = fields.Char('Dirección Receptor', size=300)
    comuna_receptor = fields.Char('Comúna Receptor', size=300)
    ciudad_receptor = fields.Char('Ciudad Receptor', size=300)
    correo_receptor = fields.Char('Correo Receptor', size=50)
    rut_mandante = fields.Char('Rut Mandante', size=10)
    medio_pago = fields.Char('Medio Pago', size=50)
    tipo_cta_pago = fields.Char('Tipo Cuenta Pago', size=50)
    numero_cta_pago = fields.Char('Numero Cuenta Pago', size=50)
    banco_pago = fields.Char('Banco Pago', size=50)
    forma_pago = fields.Char('Forma Pago', size=50)
    forma_pago_exp = fields.Char('Forma Pago Exp', size=50)
    cod_term_pago = fields.Char('Código Termino de Pago', size=50)
    dias_term_pago = fields.Char('Dias Termino de Pago', size=50)
    glosa_term_pago = fields.Char('Glosa Termino de Pago', size=200)
    ind_traslado = fields.Char('Indicador de Traslado', size=50)
    ind_servicio = fields.Char('Indicador de Servicio', size=50)
    ind_no_rebaja = fields.Char('Indicador de no Rebaja', size=50)
    tipo_despacho = fields.Char('Tipo Despacho', size=50)
    tipo_imp = fields.Char('Tipo Impuesto', size=50)
    tasa_imp = fields.Char('Tasa Impuesto', size=50)
    monto_imp = fields.Char('Monto Impuesto', size=50)
    iva_prop = fields.Char('IVA Propio', size=50)
    iva_terc = fields.Char('IVA Terceros', size=50)
    tasa_iva = fields.Char('Tasa IVA', size=50)
    IVA = fields.Char('IVA', size=50)
    monto_exento = fields.Char('Monto Excento', size=50)
    monto_neto = fields.Char('Monto Neto', size=50)
    monto_total = fields.Char('Monto Total', size=50)
    monto_bruto = fields.Char('Monto Bruto', size=50)
    monto_periodo = fields.Char('Monto Periodo', size=50)
    monto_cancelar = fields.Char('Monto Cancelar', size=50)
    monto_pagos = fields.Char('Monto Pagos', size=50)
    monto_nf = fields.Char('Monto NF', size=50)
    saldo_anterior = fields.Char('Saldo Anterior', size=50)
    saldo_insol = fields.Char('Sado Insoluble', size=50)
    tedxml = fields.Text('TedXML')
    dctos_globales = fields.Char('Descuentos Globales', size=50)
    integration_point_id = fields.Char('Punto de Integracion', size=50)
    comisiones = fields.Char('Comisiones', size=50)
    correo_emisor = fields.Char('Correo Emisor', size=50)
    extranjero_nacionalidad = fields.Char('Nacionalidad extranjera', size=50)
    extranjero_num_id = fields.Char('Numero Extranjero', size=50)
    ind_monto_neto = fields.Char('Indicador Monto Neto', size=50)
    total_periodo = fields.Char('Total Periodo', size=50)
    tipo_moneda = fields.Char('Tipo de Moneda', size=50)
    valor_exento = fields.Char('Valor Exento', size=50)
    valor_iva = fields.Char('Valor IVA', size=50)
    valor_neto = fields.Char('Valor Neto', size=50)
    valor_pagar = fields.Char('Valor pagar', size=50)
    line_ids = fields.One2many('l10n_cl_dte.document_xml_lines', 'invoice_id', 'Detalles')
    transport_ids = fields.One2many('l10n_cl_dte.document_transporte_xml', 'invoice_id', 'Transporte')
    reference_ids = fields.One2many('l10n_cl_dte.document_xml_references', 'invoice_id', 'Referencias')
    comercial_state = fields.Selection(
        [('0', 'Sin Acuse'), ('1', 'Acuse Comercial Aceptado'), ('2', 'Rechazado Comercialmente')],
        'Estado Acuse Comercial', default='0')
    merchandise_state = fields.Selection([('0', 'Sin Acuse'), ('1', 'Acuse Recibo Mercaderias y Servicios'), \
                                          ('2', 'Rechazo acuse Mercaderias y Servicios'),
                                          ('3', 'Recepcion total de Mercaderias y Servicios'),
                                          ('4', 'Reclamo por Falta Parcial de Mercaderias'),
                                          ('5', 'Reclamo por Falta Total de Mercaderias')],
                                         'Acuse Mercaderias y Servicios', default='0')
    invoice_id = fields.One2many('account.move', 'purchase_xml_id', string='Facturas')
    invoice_asoc_id = fields.Many2one('account.move', 'Factura Asociada')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get(
                                     'l10n_cl_dte.document_xml'))
    provider_id = fields.Many2one('res.partner', 'Proveedor Asociado')
    date_acuse_comercial = fields.Date('Fecha de Acuse Comercial')
    date_acuse_merchandise = fields.Date('Fecha de Acuse Mercaderia')
    pdf_img = fields.Binary('PDF Image', readonly=True)
    name_file = fields.Char(string="Nombre de Pdf", readonly=True)

    def _get_attachment_values(self, obj, attachment, type=None):
        return {
            'name': '%s.pdf' % obj.folio,
            'res_name': '%s.pdf' % obj.folio,
            'res_model': 'l10n_cl_dte.document_xml',
            'res_id': obj.id,
            'datas': attachment,
            'type': 'binary'
        }

    def imprimir_documento(self):
        track_id = factual.get_track_id(self.env.user.company_id.dte_url, self.rut_emisor, self.tipo_dte, self.folio,
                                        self.env.user.company_id.dte_user, self.env.user.company_id.dte_pass)
        if not track_id:
            raise ('No se ha podido obtener el PDF.')
        pdf = base64.encodestring(factual.get_pdf(self.env.user.company_id.dte_url, track_id))
        attch_vals = self._get_attachment_values(self, pdf, type='.pdf')
        ir_pool = self.env['ir.attachment']
        pdf_id = ir_pool.search([('name', '=', attch_vals['name']), ('res_model', '=', 'l10n_cl_dte.document_xml')])
        if not pdf_id:
            ir_pool.sudo().create(attch_vals)
        self.write({
            'pdf_img': pdf,
            'name_file': str(self.folio) + ".pdf"
        })
        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        return pdfhttpheaders

    def create_invoice(self):
        for record in self:
            data_invoice = {}
            data_invoice_line = {}
            data_invoice_line_ids = []
            data_invoice_tax = {}
            data_invoice_tax_exento = {}
            impuesto_exento = record.env['account.tax'].search(
                [('amount', '=', 0), ('type_tax_use', '=', 'purchase')], limit=1)
            imp = []
            if not impuesto_exento:
                raise exceptions.Warning(
                    'Debe crear el impuesto exento de compras.')
            if not record.provider_id:
                raise exceptions.Warning(
                    'Debe Asociar el proveedor registrado en el sistema.')
            if not record.date_account:
                raise exceptions.Warning(
                    'Debe colocar Fecha contable.')
            if record.tasa_iva:
                impuesto = record.env['account.tax'].search(
                    [('amount', '=', record.tasa_iva), ('type_tax_use', '=', 'purchase')], limit=1)
                if not impuesto:
                    raise exceptions.Warning(
                        'No hay impuesto de Compra para ' + str(record.tasa_iva) + '%')
                else:
                    imp.append(impuesto.id)
            for line in record.line_ids:
                if not line.product_id:
                    raise exceptions.Warning(
                        'Debe asociar el producto de cada item de la factura.')
            data_invoice['partner_id'] = record.provider_id.id
            document_dte = record.env['l10n_latam.document.type'].search([('code', '=', record.tipo_dte)], limit=1)
            if document_dte:
                data_invoice['l10n_latam_document_type_id'] = document_dte.id
            else:
                raise exceptions.Warning(
                    'No se encuentra registrado ese tipo de documento DTE')
            data_invoice['invoice_date'] = record.date
            data_invoice['purchase_xml_id'] = record.id
            data_invoice['invoice_date_due'] = record.date_due
            data_invoice['date'] = record.date_account
            data_invoice['reference'] = int(record.folio)
            data_invoice['team_id'] = False
            data_invoice['journal_id'] = 2
            data_invoice['l10n_latam_document_number'] = record.folio
            if record.tipo_dte in ['33', '34']:
                data_invoice['move_type'] = 'in_invoice'
            else:
                if record.tipo_dte in ['61']:
                    data_invoice['move_type'] = 'in_refund'
                else:
                    raise exceptions.Warning(
                        'No se ha definido la creacion de Nota de credito y debito')
            for line in record.line_ids:
                imp_pro = []
                if not line.product_id.supplier_taxes_id:
                    raise exceptions.Warning(
                        'Uno de los productos no tiene definido impuesto de compra')
                else:
                    imp_pro.append(line.product_id.supplier_taxes_id[0].id)
                account = line.product_id.property_account_income_id or line.product_id.categ_id.property_account_income_categ_id
                if not account:
                    raise exceptions.Warning(
                        'Debe definir las cuentas contables para este producto')
                #data_invoice_line['product_id'] = line.product_id.id
                #data_invoice_line['quantity'] = line.cantidad
                #data_invoice_line['price_unit'] = float(line.prc)
                #data_invoice_line['name'] = line.product_id.product_tmpl_id.name
                # data_invoice_line['account_id'] = line.account_id.id
                #data_invoice_line['account_id'] = account.id
                #data_invoice_line['analytic_account_id'] = line.analytic_account_id.id

                val_line = (0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.cantidad,
                    'price_unit': float(line.prc),
                    'name': line.product_id.product_tmpl_id.name,
                    'account_id': account.id,
                    'analytic_account_id': line.analytic_account_id.id,
                    'tax_ids': [(4, line.product_id.supplier_taxes_id[0].id)],
                    'display_type': False,
                })
                data_invoice_line_ids.append(val_line)
                #data_invoice_line['tax_ids'] = [(0, 0, imp_pro)]
                #data_invoice_line['tax_ids'] = [(4, line.product_id.supplier_taxes_id[0].id)]
                _logger.info('DATA INVOICE LINE')
                _logger.info(data_invoice_line)
                #record.env['account.move.line'].create(data_invoice_line)
            data_invoice['invoice_line_ids'] = data_invoice_line_ids
            _logger.info('DATA INVOICE')
            _logger.info(data_invoice)
            invoice_id = record.env['account.move'].create(data_invoice)
            #if record.tasa_iva:
            #    data_invoice_tax['invoice_id'] = invoice_id.id
            #    data_invoice_tax['name'] = impuesto.name
            #    data_invoice_tax['tax_id'] = impuesto.id
            #    data_invoice_tax['amount'] = int(record.IVA)
            #    data_invoice_tax['base'] = int(record.monto_total)
            #    data_invoice_tax['account_id'] = impuesto.account_id.id
            #    record.env['account.invoice.tax'].create(data_invoice_tax)
            #if int(record.monto_exento) > 0:
            #    data_invoice_tax_exento['invoice_id'] = invoice_id.id
            #    data_invoice_tax_exento['name'] = impuesto_exento.name
            #    data_invoice_tax_exento['tax_id'] = impuesto_exento.id
            #    data_invoice_tax_exento['amount'] = 0
            #    data_invoice_tax_exento['base'] = int(record.monto_total)
            #    data_invoice_tax_exento['account_id'] = impuesto_exento.account_id.id
            #    record.env['account.invoice.tax'].create(data_invoice_tax_exento)
            record.write({'invoice_asoc_id': invoice_id.id})
        return True


class DocumentXmlLines(models.Model):
    _name = 'l10n_cl_dte.document_xml_lines'
    _rec_name = 'detalle'

    invoice_id = fields.Many2one('l10n_cl_dte.document_xml', 'XML Compra')
    code_ids = fields.One2many('l10n_cl_dte.code_items_xml', 'line_id', 'Códigos')
    subqty_ids = fields.One2many('l10n_cl_dte.subqty_xml', 'line_id', 'Subcantidades')
    detalle = fields.Char('Detalle', size=30)
    precio_unitario = fields.Char('Precio unitario', size=30)
    cantidad = fields.Float('Cantidad')
    descuento = fields.Char('Descuento', size=30)
    impuesto = fields.Char('Impuesto', size=30)
    subtotal = fields.Float('Subtotal')
    # no incluidos en el modelo pero creados por venir en el json
    nmb_item = fields.Char('NmbItem', size=30)
    n_lineas_detalle = fields.Char('Número lineas detalle', size=30)
    prc = fields.Char('Prc Item', size=30)
    cantidad_referencial = fields.Char('Cantidad Referencial', size=30)
    unmd = fields.Char('Unidad de Medida Item', size=30)
    ind_exencion = fields.Char('Indice Exención', size=1)
    product_id = fields.Many2one('product.product', 'Producto Asociado')
    account_id = fields.Many2one('account.account', 'Cuenta Asociado')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Account Analityc')


class ReferenciasDocumentXml(models.Model):
    _name = 'l10n_cl_dte.document_xml_references'
    _rec_name = 'numero_ref'

    invoice_id = fields.Many2one('l10n_cl_dte.document_xml', 'XML Compra')
    numero_ref = fields.Char('Número Ref.', size=100)
    tipo_doc_ref = fields.Char('Tipo Documento Ref.', size=4)
    folio_ref = fields.Char('Folio Ref.', size=50)
    fecha_ref = fields.Date('Fecha Ref.')
    codigo_ref = fields.Char('Código Ref.', size=50)
    razon_ref = fields.Char('Razón Ref.', size=300)


class TransporteDocumentXml(models.Model):
    _name = 'l10n_cl_dte.document_transporte_xml'
    _rec_name = 'nombre_chofer'

    invoice_id = fields.Many2one('l10n_cl_dte.document_xml', 'Factura')
    aduana = fields.Char('Aduana', size=30)
    ciudad_destino = fields.Char('Ciudad Destino', size=30)
    comuna_destino = fields.Char('Comúna Destino', size=30)
    direccion_destino = fields.Char('Dirección Destino', size=80)
    nombre_chofer = fields.Char('Nombre Chofer', size=30)
    patente = fields.Char('Patente', size=30)
    rut_chofer = fields.Char('Rut Chofer', size=30)
    rut_transporte = fields.Char('Rut Transporte', size=30)
    

class InternalFolio(models.Model):
    _name = "internal.folio"

    @api.constrains('l10n_latam_document_type_id')
    def _check_duplicate(self):
        f_id = self.env['internal.folio'].search(
            [('company_id', '=', self.company_id.id),
             ('l10n_latam_document_type_id', '=', self.l10n_latam_document_type_id.id)])
        if len(f_id) > 1:
            raise exceptions.Warning('Ya existe una secuencia de este tipo de documento para esta empresa')

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Tipo de documento')
    sig_folio = fields.Integer('Siguiente Folio')
    company_id = fields.Many2one('res.company', 'Compañia')

