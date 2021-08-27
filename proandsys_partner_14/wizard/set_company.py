# -*- coding: utf-8 -*-


from odoo import models, fields, api, exceptions
from collections import OrderedDict
from .. tools.api import factual


class SetCompanyDte(models.TransientModel):
	_name = 'set.company.dte'

	resolution_date = fields.Date('Fecha Resolución', required=True)
	resolution_number = fields.Char('Número Resolución', required=True)

	def set_company(self):
		company_pool = self.env['res.company']
		if 'active_id' in self._context:
			data = OrderedDict()
			
			wizard = self
			company = company_pool.browse(self._context['active_id'])

			if company.partner_id.vat:
				data['Code'] = company.partner_id.vat
			else:
				raise exceptions.Warning('Debe establecer una rutina para el socio de la empresa.')
			data['Name'] = company.partner_id.name
			if company.partner_id.email:
				data['ContactEmail'] = company.partner_id.email
			else:
				raise exceptions.Warning('Debe configurar un correo electrónico para el socio de la empresa.')
			if company.sii_suc:
				data['SiiOffice'] = company.sii_suc
			else:
				raise exceptions.Warning('Debe configurar la Oficina SII perteneciente a la empresa.')
			if company.partner_id.giro:
				data['Giro'] = company.partner_id.giro
			else:
				raise exceptions.Warning('Debe establecer un giro para el socio de la empresa.')
			if company.partner_id.street and company.partner_id.street2:
				data['Address'] = '%s %s' % (company.partner_id.street, company.partner_id.street2)
			elif company.partner_id.street:
				data['Address'] = company.partner_id.street
			elif company.partner_id.street2:
				data['Address'] = company.partner_id.street2
			else:
				raise exceptions.Warning('Debe establecer una calle para el socio seleccionado.')
			if company.partner_id.city:
				data['City'] = company.partner_id.city
			else:
				raise exceptions.Warning('Debe establecer una ciudad para el socio de la empresa.')
			if company.partner_id.state_id:
				data['Comuna'] = company.partner_id.state_id.name
			else:
				raise exceptions.Warning('Debe establecer una comuna para el socio de la empresa.')
			if company.partner_id.economic_act_ids:
				data['Acteco'] = company.partner_id.economic_act_ids[0].code
			else:
				raise exceptions.Warning('Debe establecer una actividad económica para el socio de la empresa.')
			data['ResolutionDate'] = wizard.resolution_date
			data['ResolutionNumber'] = wizard.resolution_number
			data['SiiSender'] = True

			res = factual.set_company(company.dte_url, data, company.dte_user, company.dte_pass)
			if not res['Status']:
				raise exceptions.Warning('Se ha producido un error al intentar registrar su empresa.\n'+\
										'El error es el siguiente: '+str(res['Description']))
			else:
				company.set_company_img(user=res['IntegrationPoint'], passwd=res['Password'])
				company.write({'dte_user': res['IntegrationPoint'],
								'dte_pass': res['Password'],
								'resolution_date': data['ResolutionDate'],
								'resolution_number': data['ResolutionNumber']})
			
		return True
