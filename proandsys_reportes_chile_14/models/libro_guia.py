from odoo import models, fields, api, exceptions
from collections import OrderedDict
from datetime import date,datetime
import pandas as pd
import logging

_logger = logging.getLogger(__name__)


class libro_guia_proandsys_reportes_chile_14(models.TransientModel):
    _inherit = 'wizard.reportes.chile'    

    
    def _libro_guias(self,wizard=False):
        if wizard:  
            wiz = self.search([('id','=',wizard)])
        else:
            wiz = self 
        search_domain = wiz._get_domain()
        search_domain += [
            ('state','in',['done']),
            ('l10n_latam_document_number','!=',False)           
            ]
        docs = wiz.env['l10n_cl.dte.stock'].search(search_domain, order='l10n_latam_document_number asc')
        #if not docs:
        #    raise exceptions.Warning('No hay datos para mostrar con los filtros actuales')        
        if docs:
            dic = OrderedDict([
                ('Numero',''),
                ('Tipo de operacion',''),
                ('Fecha',''),
                ('RUT',''),
                ('Cliente',''),
                ('Origen',''),
                # ('Folio doc referencia',''),
                # ('Fecha doc referencia',''),
                ('Neto',''),
                ('Impuesto',''),
                ('Total',''),
                ])
            lista = []
            for i in docs:
                dicti = OrderedDict()
                dicti.update(dic)
                dicti['Numero']=i.l10n_latam_document_number 
                dicti['Tipo de operacion']=dict(i.fields_get(allfields=['move_index'])['move_index']['selection'])[i.move_index]
                dicti['Fecha']=i.date
                dicti['RUT']=i.partner_id.vat
                dicti['Cliente']=i.partner_id.name
                dicti['Origen']=i.picking_id.origin
                # dicti['Folio doc referencia']=i.move_id.l10n_latam_document_number
                # dicti['Fecha doc referencia']=i.move_id.invoice_date.strftime('%d-%m-%Y')
                dicti['Neto']=i.amount_untaxed
                dicti['Impuesto']=i.amount_tax
                dicti['Total']=i.amount_total 
                lista.append(dicti)    
            tabla = pd.DataFrame(lista)
        else:
            tabla = pd.DataFrame([])  
        return tabla 

# class libro_guias_picking_inherit(models.Model):
#     _inherit = 'stock.picking'

#     period_id  = fields.Many2one('account.period', store=True, compute='get_period')

#     
#     @api.depends('date_done')
#     def get_period(self):
#         for record in self:
#             if record.date_done:
#                 fecha = datetime.strptime(record.date_done, '%Y-%m-%d %H:%M:%S')
#                 period = datetime.strftime(fecha, '%m/%Y')
#                 period_search = self.env['account.period'].search([('name','=', period)])
#                 if period_search:
#                     record.period_id = period_search[0].id