from odoo import models, fields, api, exceptions
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import OrderedDict
import pandas as pd
import logging

_logger = logging.getLogger(__name__)


class libro_hono_proandsys_reportes_chile_14(models.TransientModel):
    _inherit = 'wizard.reportes.chile'    

    
    def _libro_honorarios(self,wizard=False):
        if wizard:  
            wiz = self.search([('id','=',wizard)])
        else:
            wiz = self                
        search_domain = wiz._get_domain()
        search_domain += [
            ('state','=','posted'),            
            ('move_type','in',['in_invoice']),
            ('l10n_latam_document_type_id.code','in',['71'])   
            ]  
        docs = wiz.env['account.move'].search(search_domain, order='ref asc')
        #if not docs:
        #    raise exceptions.Warning('No hay datos para mostrar con los filtros actuales')        
        if docs:
            dic = OrderedDict([
                ('Tipo',''),
                ('Numero',''),
                ('Fecha',''),
                ('RUT',''),
                ('Nombre',''),
                ('Bruto',''),
                ('Retencion',''),
                ('A pagar',''),
                ])
            lista = []
            for i in docs:
                dicti = OrderedDict()
                dicti.update(dic)
                dicti['Tipo']='BH'
                dicti['Numero']=i.ref
                dicti['Fecha']=i.invoice_date.strftime('%d-%m-%Y')
                dicti['RUT']=i.partner_id.vat
                dicti['Nombre']=i.partner_id.name
                dicti['Bruto']=abs(i.amount_untaxed_signed)
                dicti['Retencion']=abs(i.amount_tax)
                dicti['A pagar']=i.amount_total 
                lista.append(dicti)    
            tabla = pd.DataFrame(lista)  
        else:
            tabla = pd.DataFrame([])
        return tabla 