# -*- coding: utf-8 -*-

import base64
from .. tools.api import factual
from collections import OrderedDict
from odoo import models, fields, api, exceptions

import logging
logger = logging.getLogger(__name__)


class Ecerts(models.Model):
    _name = 'l10n_cl_dte.ecert'
    _description = 'E-Certs maintainers'

    @api.model
    def create(self, vals):
        data = OrderedDict()
        company_pool = self.env['res.company']

        res = super(Ecerts, self).create(vals)
        company = company_pool.browse(vals['company_id'])

        data['CertificateBase64'] = vals['ecert']
        data['Password'] = vals['password']
        data['OwnerRut'] = vals['owner_rut']
        data['CompanyRut'] = company.partner_id.vat

        status = factual.set_cert(company.dte_url, data, user=company.dte_user, passwd=company.dte_pass)
        if not status['Status']:
            raise ('Error!', 'Se ha producido un error al intentar cargar su certificado.\n' + \
                   'El error es el siguiente:\n' + str(status['Description']))
        return res

    def write(self, vals):
        company_pool = self.env['res.company']
        data = OrderedDict()
        res = super(Ecerts, self).write(vals)

        for cert in self:
            company = company_pool.browse(vals['company_id'] if 'company_id' in vals else cert.company_id.id)
            data['CertificateBase64'] = vals['ecert'] if 'ecert' in vals else cert.ecert
            data['Password'] = vals['password'] if 'password' in vals else cert.password
            data['OwnerRut'] = vals['owner_rut'] if '' in vals else cert.owner_rut
            data['CompanyRut'] = company.partner_id.vat

            status = factual.set_cert(company.dte_url, data, user=company.dte_user, passwd=company.dte_pass)
            if not status['Status']:
                raise ('Error!', 'Se ha producido un error al intentar cargar su certificado.\n' + \
                       'El error es el siguiente:\n' + str(status['Description']))
        return res

    company_id = fields.Many2one('res.company', 'Compañia')
    name = fields.Char('Nombre', size=64, required=True)
    password = fields.Char('Contraseña', size=64, required=True)
    owner_rut = fields.Char('Owner Rut', size=11, required=True)
    ecert = fields.Binary('E-cert', required=True, filters='*.pem,*.cert,*.cer,*.certificate,*.pfx,*.aspx,*.kdc')
    sequence = fields.Integer('Secuencia')


class ResCompanyDte(models.Model):
    _inherit = 'res.company'

    ecert = fields.One2many('l10n_cl_dte.ecert', 'company_id', 'E-Cert')
    dte_user = fields.Char('Usuario DTE', size=60)
    dte_pass = fields.Char('Clave DTE', size=60)
    dte_url = fields.Char('URL DTE')
    resolution_number = fields.Integer('Número de Resolución')
    resolution_date = fields.Date('Fecha de Resolución')
    sii_suc = fields.Char('Oficina SII', size=60)
    proxy_ip = fields.Char('Dirección IP', help='El nombre de host o la dirección IP del proxy de hardware, se detectará automáticamente si se deja vacío', size=45)
    internal_pdf = fields.Boolean('PDF Interno')
    ind_folios = fields.Selection([('1', 'Internos'), ('2', 'Producción')],
                                  'Usar Folios', default='1', readonly=False, required=True)
    sii_doc_type_id = fields.Many2one('l10n_latam.document.type', 'Tipo de documento por Defecto')

    def set_company_img(self, user=None, passwd=None):
        for comp in self:
            res = factual.set_com_img(comp.dte_url, base64.decodebytes(comp.logo), \
                        comp.partner_id.vat, user=comp.dte_user if comp.dte_user else user,\
                             passwd=comp.dte_pass if comp.dte_pass else passwd)
            if not res['Status']:
                raise exceptions.Warning('Error!', \
                    'Ha ocurrido un error al enviar los datos, favor contacte con su administrador de sistemas.\n'+\
                    str(res['Description']))
        return True

    def get_notifications(self):
        nots = OrderedDict()
        group_ids = []
        res_pool = self.env['res.users']
        data_pool = self.env['ir.model.data']
        icp_pool = self.env['ir.config_parameter']
        for comp in self:
            nots['CompanyRut'] = comp.partner_id.vat or ''
            if not comp.dte_user:
                raise exceptions.Warning('Error!', 'No seencuentra el campo Usuario DTE, esto puede deberse a que no ha '+\
                                'configurado la empresa en el sistema o que ha habido un problema al procesar '+\
                                'la respuesta, por favor, intente configurar nuevamente.')
            nots['User'] = comp.dte_user
            nots['Password'] = comp.dte_pass
            if icp_pool.get_param('web.base.url.freeze'):
                nots['Target'] = icp_pool.get_param('web.base.url.freeze')
            else:
                nots['Target'] = icp_pool.get_param('web.base.url')
            nots['Protocol'] = 'HTTP'
            nots['Format'] = 'JSON'
            nots['Db'] = str(self._cr.dbname)
            logger.info('SET NOTIFICATION')
            logger.info(comp.dte_url)
            logger.info(nots)
            res = factual.set_notification(url=comp.dte_url, data=nots, user='81895441-64d5-4ea3-81bb-55e73be4cfbe', passwd='zKHbvBHeIU1088X')
            if not res['Status']:
                raise exceptions.Warning('Ha ocurrido un error al enviar los datos, favor contacte con su administrador de sistemas.' + str(res['Description']))
            else:
                a = res_pool.search([('login', '=', '81895441-64d5-4ea3-81bb-55e73be4cfbe'), ('active', '=', True)], limit=1)
                if not a.id:
                    group_ids.append(data_pool.get_object_reference('proandsys_partner_14', 'group_dte_manager')[1])
                    group_ids.append(data_pool.get_object_reference('account', 'group_account_manager')[1])
                    user = res_pool.create({
                        'login': '81895441-64d5-4ea3-81bb-55e73be4cfbe', 'active': True,
                        'password': 'zKHbvBHeIU1088X', 'name': 'Factual',
                        'groups_id': [(6, 0, group_ids)]})
                    user.partner_id.write({'email': 'info@proandsys.net'})
        return True


class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    rate = fields.Float(digits=(12, 20), help='La tasa de la moneda a la moneda de la tasa 1')


class Currency(models.Model):
    _inherit = "res.currency"

    rate = fields.Float(compute='_compute_current_rate', string='Tasa actual', digits=(12, 20),
                        help='La tasa de la moneda a la moneda de la tasa 1.')