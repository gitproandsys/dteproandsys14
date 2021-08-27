# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class ResPartnerPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\n%(city)s %(state_name)s %(zip)s\n%(country_name)s"

    giro = fields.Char('Giro', size=200)
    nombre_fantasia = fields.Char('Nombre de Fantasia', size=200)
    economic_act_ids = fields.Many2many('economic.activity', string='Actividades Economicas')
    coface = fields.Boolean('COFACE')
    dicom = fields.Boolean('DICOM')
    porcentaje = fields.Float('Procentaje Adicional L.C')
    email_dte = fields.Char('Email DTE',
                            help='Este email es utilizado para distribuir los PDF y XML generados aparte de los distribuidos normalmente por el sistemas de SII.')
    email_cesor = fields.Char('Email Cesor',
                              help='Este email es utilizado como email de contacto al ceder un Documento.')
    cesionario = fields.Boolean('Es Cesionario',
                                help='Marcar este campo para hacer que el partner pueda recibir cesiones DTE.')

    contacto_invoice_id = fields.Many2one('res.partner', 'Contacto de Facturación',
                                          domain="[('parent_id','=',id),('type','=','contact')]", readonly=False,
                                          required=False)
    contacto_collection_id = fields.Many2one('res.partner', 'Contacto de Cobranzas',
                                             domain="[('parent_id','=',id),('type','=','contact')]", readonly=False,
                                             required=False)
    

class ResUsersDte(models.Model):
    _inherit = 'res.users'

    ecert = fields.Many2one('l10n_cl_dte.ecert', 'E-Cert')