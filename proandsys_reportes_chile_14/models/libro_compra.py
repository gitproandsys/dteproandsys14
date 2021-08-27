from odoo import models, fields, api, exceptions
from collections import OrderedDict
import pandas as pd
import logging

_logger = logging.getLogger(__name__)


class libro_compra_proandsys_reportes_chile_14(models.TransientModel):
    _inherit = 'wizard.reportes.chile' 

    
    def _facturas_libro_compra(self): 
        search_domain = self._get_domain()
        search_domain += [
            ('state','=','posted'),            
            ('move_type','in',['in_invoice']),
            ('l10n_latam_document_type_id.code','in',['30','32','33','34','45','55','56'])  
            ]  
        docs = self.env['account.move'].search(search_domain, order='ref asc')
        impuestos_obj = self.env['account.tax'].search([
            ('mostrar_c','=',True),
            ('company_id','=',self.company_id.id)])
        dic = OrderedDict([
            ('Tipo',''),
            ('Numero',''),
            ('Fecha',''),
            ('Rut',''),
            ('Cliente',''),
            ('Exento',0),
            ('Neto',0),            
            ])
        for record in impuestos_obj:
            dic.update({record.name:0})
        dic.update({'Total Impuestos':0}) 
        dic.update({'Total':0})    
        lista = []
        for i in docs:
            dict = OrderedDict()
            dict.update(dic)
            dict['Tipo']=i.l10n_latam_document_type_id.name
            dict['Numero']=i.ref
            dict['Fecha']=i.invoice_date.strftime('%d-%m-%Y')
            dict['Rut']=i.partner_id.vat
            dict['Cliente']=i.partner_id.name
            dict['Exento']=sum(i.invoice_line_ids.filtered(lambda r: r.tax_ids == False).mapped('price_subtotal'))
            dict['Neto']=i.amount_untaxed
            for group_imp in i.amount_by_group:
                dict['Total Impuestos']+=group_imp[1] if  group_imp[1] > 0 else 0
            dict['Total']=i.amount_total
            for imp in i.line_ids.filtered(lambda r: r.name in dic.keys()):
                dict[imp.name]+=imp.price_subtotal
            lista.append(dict)                              
        tabla = pd.DataFrame(lista)            
        return tabla 
            # dict['IVA 19% Compra']=i._l10n_cl_get_amounts()['vat_amount']

    
    def _nc_libro_compra(self): 
        search_domain = self._get_domain()
        search_domain += [
            ('state','=','posted'),            
            ('move_type','in',['in_refund']),
            ('l10n_latam_document_type_id.code','in',['60','61'])
            ] 
        docs = self.env['account.move'].search(search_domain, order='ref asc')
        impuestos_obj = self.env['account.tax'].search([
            ('mostrar_c','=',True),
            ('company_id','=',self.company_id.id)])
        dic = OrderedDict([
            ('Tipo',''),
            ('Numero',''),
            ('Fecha',''),
            ('Rut',''),
            ('Cliente',''),
            ('Exento',0),
            ('Neto',0),            
            ])
        for record in impuestos_obj:
            dic.update({record.name:0})
        dic.update({'Total Impuestos':0})
        dic.update({'Total':0})    
        lista = []
        for i in docs:
            dict = OrderedDict()
            dict.update(dic)
            dict['Tipo']=i.l10n_latam_document_type_id.name
            dict['Numero']=i.ref
            dict['Fecha']=i.invoice_date.strftime('%d-%m-%Y')
            dict['Rut']=i.partner_id.vat
            dict['Cliente']=i.partner_id.name
            dict['Exento']=sum(i.invoice_line_ids.filtered(lambda r: r.tax_ids == False).mapped('price_subtotal'))
            dict['Neto']=-i.amount_untaxed
            for group_imp in i.amount_by_group:
                dict['Total Impuestos']+=-group_imp[1] if  group_imp[1] > 0 else 0
            dict['Total']=-i.amount_total
            for imp in i.line_ids.filtered(lambda r: r.name in dic.keys()):
                dict[imp.name]+=-imp.price_subtotal
            lista.append(dict)  
        tabla = pd.DataFrame(lista)            
        return tabla

    
    def _din_libro_compra(self): 
        search_domain = self._get_domain()
        search_domain += [
            ('state','in',['done'])            
            ] 
        docs = self.env['account.din'].search(search_domain, order='origin asc') 
        impuestos_obj = self.env['account.tax'].search([
            ('mostrar_c','=',True),
            ('company_id','=',self.company_id.id)])       
        dic = OrderedDict([
            ('Tipo',''),
            ('Numero',''),
            ('Fecha',''),
            ('Rut',''),
            ('Cliente',''),
            ('Exento',0),
            ('Neto',0)
            ])
        for record in impuestos_obj:
            dic.update({record.name:0})
        dic.update({'Total Impuestos':0})
        dic.update({'Total':0})           
        lista = []
        for i in docs:
            dict = OrderedDict()
            dict.update(dic)
            dict['Tipo']=i.journal_id.name
            dict['Numero']=i.origin
            dict['Fecha']=i.date_din
            dict['Rut']=i.partner_id.vat
            dict['Cliente']=i.partner_id.name
            dict['Neto']=i.total_untaxed   
            dict['Total Impuestos']=i.amount_tax         
            dict['Total']=i.amount_total            
            lista.append(dict)                              
        tabla = pd.DataFrame(lista)            
        return tabla
   
    def _facturas_terceros(self):
        search_domain = self._get_domain()
        search_domain += [
            ('state','=','posted'),            
            ('move_type','in',['in_invoice']),
            ('l10n_latam_document_type_id.code','in',['46'])
            ] 
        docs = self.env['account.move'].search(search_domain, order='ref asc')
        impuestos_obj = self.env['account.tax'].search([
            ('mostrar_c','=',True),
            ('company_id','=',self.company_id.id)])
        dic = OrderedDict([
            ('Tipo',''),
            ('Numero',''),
            ('Fecha',''),
            ('Rut',''),
            ('Cliente',''),
            ('Exento',0),
            ('Neto',0),            
            ])
        for record in impuestos_obj:
            dic.update({record.name:0})
        dic.update({'Total Impuestos':0})
        dic.update({'Total':0})    
        lista = []
        for i in docs:
            dict = OrderedDict()
            dict.update(dic)
            dict['Tipo']=i.l10n_latam_document_type_id.name
            dict['Numero']=i.ref
            dict['Fecha']=i.invoice_date.strftime('%d-%m-%Y')
            dict['Rut']=i.partner_id.vat
            dict['Cliente']=i.partner_id.name
            dict['Exento']=sum(i.invoice_line_ids.filtered(lambda r: r.tax_ids == False).mapped('price_subtotal'))
            dict['Neto']=i.amount_untaxed
            for group_imp in i.amount_by_group:
                dict['Total Impuestos']+=group_imp[1] if  group_imp[1] > 0 else 0
            dict['Total']=i.amount_total
            for imp in i.line_ids.filtered(lambda r: r.name in dic.keys()):
                dict[imp.name]+=imp.price_subtotal
            lista.append(dict)                              
        tabla = pd.DataFrame(lista)            
        return tabla 
    
    def _resumen_libro_compra(self): 
        tabla1 = self._facturas_libro_compra()
        tabla2 = self._nc_libro_compra()
        tabla3 = self._din_libro_compra()
        tabla4 = self._facturas_terceros()
        union = pd.concat([tabla1,tabla2,tabla3,tabla4])
        # union = pd.concat([tabla1,tabla2])
        if not union.empty:
	        union = union.drop(['Fecha','Rut','Cliente'], axis=1)
	        columnas = list(union)
	        aggregations = OrderedDict()
	        for record in columnas:
	            aggregations.update([(record,'sum')])        
	        aggregations['Numero']='count'
	        aggregations['Tipo']='max'
	        #aggregations.pop('Tipo', None)
	        union = pd.DataFrame(union.groupby('Tipo').agg(aggregations))
        return union.fillna(0)


    
    def _tabla_libro_compra(self,wizard=False):  
        if wizard:  
            wiz = self.search([('id','=',wizard)])
        else:
            wiz = self
        tabla1 = wiz._facturas_libro_compra()
        tabla2 = wiz._nc_libro_compra()
        tabla3 = wiz._din_libro_compra()
        tabla4 = wiz._facturas_terceros()
        union = pd.concat([tabla1,tabla2,tabla3,tabla4])
        # union = pd.concat([tabla1,tabla2])
        return union.fillna(0)
