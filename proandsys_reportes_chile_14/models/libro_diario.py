from odoo import models, fields, api, exceptions
from collections import OrderedDict
import pandas as pd
import logging

_logger = logging.getLogger(__name__)


class libro_diario_proandsys_reportes_chile_14(models.TransientModel):
    _inherit = 'wizard.reportes.chile'  

    
    def search_libro_diario(self):        
        search_domain = [
            ('state','in',['valid']),
            ('company_id','=',self.company_id.id),
            ('move_id.state','=', 'posted')
            ]  
        if self.period_ids:
        	search_domain.append(('move_id.period_id','in', self.period_ids.ids))
        return search_domain


    
    def _libro_diario(self,wizard=False):
        if wizard:  
            wiz = self.search([('id','=',wizard)])
        else:
            wiz = self   
        search_domain = wiz._get_domain()
        search_domain += [('move_id.state','=', 'posted')]  
        docs = wiz.env['account.move.line'].search(search_domain, order='date asc')
        #if not docs:
        #    raise exceptions.Warning('No hay datos para mostrar con los filtros actuales')        
        if docs:
            dic = OrderedDict([
                	('Fecha',''),
                	('Comprobante',''),
                	('Rut',''),
                	('Partner',''),
                	('Cuenta',''),
                	('Glosa',''),
                	('Documento',''),
                	('Debe',''),
                	('Haber',''),                  
                	])
            lista = []
            for i in docs:
            	dicti = OrderedDict()
            	dicti.update(dic)
            	dicti['Fecha']=i.date         
            	dicti['Comprobante']=i.move_id.name
            	dicti['Rut']=i.partner_id.vat
            	dicti['Partner']=i.partner_id.name
            	dicti['Cuenta']=i.account_id.name
            	dicti['Glosa']=i.ref
            	dicti['Documento']=i.name 
            	dicti['Debe']=i.debit   
            	dicti['Haber']=i.credit                       
            	lista.append(dicti)    
            tabla = pd.DataFrame(lista).sort_values(['Fecha', 'Comprobante'], ascending=[1, 1])          
        else:
            tabla = pd.DataFrame([])
        return tabla 

