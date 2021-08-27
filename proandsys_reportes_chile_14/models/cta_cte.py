from odoo import models, fields, api, exceptions
from collections import OrderedDict
import pandas as pd
import logging

_logger = logging.getLogger(__name__)


class cta_cte_proandsys_reportes_chile_14(models.TransientModel):
    _inherit = 'wizard.reportes.chile'    

    
    def _get_domain_fa(self):
        search_domain=[]        
        search_domain = [            
        ('account_internal_type','in', ['receivable','payable'])
        ]         
        if self.acount_ids:
            search_domain.append(('account_id','in', self.acount_ids.ids))        
        search_domain.append(('company_id','=',self.company_id.id))                
        if self.partner_ids:
            search_domain.append(('partner_id', 'in', self.partner_ids.ids))            
        if self.fecha_inicio:
            search_domain += [('date', '>=', self.fecha_inicio)]
        if self.fecha_term:
            search_domain += [('date', '<=', self.fecha_term)]
        if self.section_id:
            search_domain.append(('section_id','=', self.section_id.id))   
        search_domain+=['|',('full_reconcile_id','=', False),('full_reconcile_id.create_date','>', self.fecha_term)]
        return search_domain  

    
    def _facturas_abiertas(self,wizard=False):         
        if wizard:  
            wiz = self.search([('id','=',wizard)])
        else:
            wiz = self  
        search_domain = wiz._get_domain_fa()        
        docs = wiz.env['account.move.line'].search(search_domain, order='date asc')
        dic = OrderedDict([
            ('Nombre',''),
            ('RUT',''),
            # ('Teléfono',''),
            # ('Dirección',''),
            ('Canal de Ventas',''),
            ('Vendedor',''),
            ('Fecha',''),
            ('Periodo',''),
            ('Referencia',''),
            ('Cuenta',''),
            ('Fecha Venc.',''),
            ('Fecha Conciliación',''),
            ('Débito',''),
            ('Crédito',''),
            ('Saldo',''),
            ])
        lista = []
        for i in docs:
            #if i.reconcile_id:
            #    if i.reconcile_id.create_date<fecha:
            #        pass
            dicti = OrderedDict()
            dicti.update(dic)
            dicti['Nombre'] = i.partner_id.name
            dicti['RUT'] = i.partner_id.vat
            dicti['Canal de Ventas'] = i.move_id.team_id.name
            dicti['Vendedor'] = i.move_id.user_id.name
            # dicti['TELEFONO'] = i.partner_id.phone or ''

            # partner_street = [i.partner_id.street] if i.partner_id.street else []
            # partner_state = [i.partner_id.state_id.name] if i.partner_id.state_id else []
            # dicti['DIRECCION'] = ' '.join(partner_street + partner_state)

            if i.date:
                dicti['Fecha'] = i.date.strftime('%d-%m-%Y')
                dicti['Periodo'] = i.date.strftime('%d-%m-%Y')
            dicti['Referencia'] = (i.move_id.ref or i.move_id.l10n_latam_document_number or i.ref)
            dicti['Cuenta'] = i.account_id.name
            if i.date_maturity:
                dicti['Fecha Venc.'] = i.date_maturity.strftime('%d-%m-%Y')
            if i.full_reconcile_id:
                dicti['Fecha Conciliación'] = i.full_reconcile_id.create_date.strftime('%d-%m-%Y')
            dicti['Débito'] = i.debit
            dicti['Crédito'] = i.credit
            dicti['Saldo'] = i.debit-i.credit         
            lista.append(dicti)
        tabla = pd.DataFrame(lista)
        return tabla.fillna(0)

