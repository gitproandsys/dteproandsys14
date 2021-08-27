# -*- coding: utf-8 -*-

from .. tools.api import factual
from collections import OrderedDict
from openerp import models, fields, api, exceptions
import logging
#Get the logger
_logger = logging.getLogger(__name__)


class SendAckWizard(models.TransientModel):
	_name= 'send.ack.wizard'
	_rec_name = 'state'

	state = fields.Selection([('0','Aceptado'),('1','Aceptado con Discrepancias'),('2','Rechazado'),('3','Recepcion total de Mercaderias y Servicios'),('4','Reclamo por Falta Parcial de Mercaderias'),('5','Reclamo por Falta Total de Mercaderias')], 'State', default='0')
	ack_type = fields.Selection([('2','Comercial'),('3','Mercaderia')], 'Ack Type', default='2')
	contact_name = fields.Char('Contact Name')
	contact_email = fields.Char('Contact Email')
	note = fields.Text('Glosa')
	company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)

	def send_ack(self):
		data = OrderedDict()		
		document_pool = self.env['l10n_cl_dte.document_xml']

		for wizard in self:
			document = document_pool.browse(self._context['active_id'])
			if document.comercial_state != '0' and document.merchandise_state != '0':
				raise exceptions.Warning('Usted ya ha dado acuse de aceptacion comercial y ecepcion de mercaderia a este documento.')
			#if document.forma_pago == '1':
			#	raise exceptions.Warning('No se puede dar acuse a una factura al contado')
			if wizard.ack_type == '2' and document.comercial_state != '0':
				raise exceptions.Warning('Usted ya ha dado acuse de aceptacion comercial a este documento.')
			elif wizard.ack_type == '3' and document.merchandise_state != '0':
				raise exceptions.Warning('Usted ya ha dado acuse de recepcion de mercaderia a este documento.')
			if document.integration_point_id:
				track_id = document.integration_point_id
			else:
				status = factual.get_dte_info(document.company_id.dte_url, document.rut_emisor, document.tipo_dte, document.folio, document.company_id.dte_user, document.company_id.dte_pass)
				track_id = status.get('TrackId', False)
				#if not track_id:
				#	raise osv.except_osv('Error', status['Description'])

			data = {
				#'DocumentId': track_id,
				'RUTEmisor': document.rut_emisor,
				'TipoDTE': document.tipo_dte,
				'Folio': document.folio,
				'TipoAcuse': wizard.ack_type,
				'Estado': wizard.state,
				'Glosa': wizard.note,
				'NombreContacto': wizard.contact_name,
				'EmailContacto': wizard.contact_email,
#				'Recinto': 'Head Office' if wizard.enclosure == head_office else 'Subsidiary'
			}			

			resp = factual.send_ack_dte(wizard.company_id.dte_url, data, wizard.company_id.dte_user, wizard.company_id.dte_pass)

			if resp['Status'] == 0:
				raise exceptions.Warning('Ha ocurrido el siguiente error: \n%s \n%s' % (resp,data))
			else:
				if wizard.ack_type == '2' and wizard.state != '2':
					document.write({'integration_point_id': track_id, 'comercial_state': '1'})
				elif wizard.ack_type == '2' and wizard.state == '2':
					document.write({'integration_point_id': track_id, 'comercial_state': '2'})
				elif wizard.ack_type == '3' and wizard.state != '2':
					document.write({'integration_point_id': track_id, 'merchandise_state': '1'})
				elif wizard.ack_type == '3' and wizard.state == '2':
					document.write({'integration_point_id': track_id, 'merchandise_state': '2'})
				elif wizard.ack_type == '3' and wizard.state == '3':
					document.write({'integration_point_id': track_id, 'comercial_state': '3'})
				elif wizard.ack_type == '3' and wizard.state == '4':
					document.write({'integration_point_id': track_id, 'merchandise_state': '4'})
				elif wizard.ack_type == '3' and wizard.state == '5':
					document.write({'integration_point_id': track_id, 'merchandise_state': '5'})
					
		return True
