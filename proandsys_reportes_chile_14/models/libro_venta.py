from odoo import models, fields, api, exceptions
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import OrderedDict
import pandas as pd
import logging

_logger = logging.getLogger(__name__)


class libro_venta_proandsys_reportes_chile_14(models.TransientModel):
    _inherit = 'wizard.reportes.chile'        

    
    def _facturas_libro_venta(self): 
        search_domain = self._get_domain()
        search_domain += [
            ('state','=','posted'),            
            ('move_type','in',['out_invoice']),
            ('l10n_latam_document_type_id.code','in',['30','32','33','34','46','56','110','111','190'])
            ] 
        docs = self.env['account.move'].search(search_domain, order='l10n_latam_document_number asc')
        impuestos_obj = self.env['account.tax'].search([
            ('mostrar_v','=',True),
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
            dict['Numero']=i.l10n_latam_document_number
            dict['Fecha']=i.invoice_date.strftime('%d-%m-%Y')
            dict['Rut']=i.partner_id.vat
            dict['Cliente']=i.partner_id.name
            if i.currency_id.name != 'CLP':
                dict['Exento']=i.amount_untaxed_signed
                dict['Total']=i.amount_total_signed
                dict['Neto']=i.amount_untaxed_signed
            else:
                dict['Exento']=sum(i.invoice_line_ids.filtered(lambda r: r.tax_ids == False).mapped('price_subtotal'))
                dict['Total']=i.amount_total
                dict['Neto']=i.amount_untaxed
            #TODO: Esto se hizo diferente en el L. de compra, falta validar si sirve para este libro
            dict['Total Impuestos']=i.amount_tax

            for imp in i.line_ids.filtered(lambda r: r.name in dic.keys()):
                dict[imp.name]+=imp.price_subtotal
            lista.append(dict)                              
        tabla = pd.DataFrame(lista)            
        return tabla 

    
    def _nc_libro_venta(self): 
        search_domain = self._get_domain()
        search_domain += [
            ('state','=','posted'),
            ('move_type','in',['out_refund'])
            ]  
        docs = self.env['account.move'].search(search_domain, order='l10n_latam_document_number asc')
        impuestos_obj = self.env['account.tax'].search([
            ('mostrar_v','=',True),
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
            dict['Numero']=i.l10n_latam_document_number
            dict['Fecha']=i.invoice_date.strftime('%d-%m-%Y')
            dict['Rut']=i.partner_id.vat
            dict['Cliente']=i.partner_id.name
            if i.currency_id.name != 'CLP':
                dict['Exento']=i.amount_untaxed_signed * -1
                dict['Total']=-i.amount_total_signed
                dict['Neto']=-i.amount_untaxed_signed
            else:
                dict['Exento']=sum(i.invoice_line_ids.filtered(lambda r: r.tax_ids == False).mapped('price_subtotal'))
                dict['Total']=-i.amount_total
                dict['Neto']=-i.amount_untaxed
            dict['Total Impuestos']=-i.amount_tax

            for imp in i.line_ids.filtered(lambda r: r.name in dic.keys()):
                dict[imp.name]+=-imp.price_subtotal
            lista.append(dict)                              
        tabla = pd.DataFrame(lista)            
        return tabla 

    
    def _boletas_libro_venta(self): 
        search_domain = self._get_domain()
        search_domain += [
            ('state','=','posted'),            
            ('move_type','in',['out_invoice']),
            ('l10n_latam_document_type_id.code','in',['35','38','39'])
            ]
        docs = self.env['account.move'].search(search_domain, order='l10n_latam_document_number asc')
        impuestos_obj = self.env['account.tax'].search([
            ('mostrar_v','=',True),
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
            dict['Numero']=i.l10n_latam_document_number
            dict['Fecha']=i.invoice_date.strftime('%d-%m-%Y')
            dict['Rut']=i.partner_id.vat
            dict['Cliente']=i.partner_id.name
            dict['Exento']=sum(i.invoice_line_ids.filtered(lambda r: r.tax_ids == False).mapped('price_subtotal'))
            dict['Neto']=i.amount_untaxed
            dict['Total Impuestos']=i.amount_tax
            dict['Total']=i.amount_total            
            for imp in i.line_ids.filtered(lambda r: r.name in dic.keys()):
                dict[imp.name]+=imp.price_subtotal
            lista.append(dict)                              
        tabla = pd.DataFrame(lista)            
        return tabla

    
    def _resumen_boletas_libro_venta(self):        
        tabla = self._boletas_libro_venta() 
        if not tabla.empty:       
            tabla = tabla.rename(
                columns={
                'Tipo':'Dia',            
                'Numero':'Primera Boleta',
                'Rut':'Ultima Boleta',
                'Cliente':'Cantidad de Boletas'
                })
            tabla['Dia'] = tabla['Fecha']
            tabla = tabla.drop(['Fecha'], axis=1)                
            aggregations = OrderedDict()
            for record in tabla.columns.values:
                aggregations.update([(record,'sum')]) 
            aggregations['Dia']='max'      
            aggregations['Primera Boleta']='min'
            aggregations['Ultima Boleta']='max'
            aggregations['Cantidad de Boletas']='count'        
            tabla = pd.DataFrame(tabla.groupby('Dia').agg(aggregations))
        return tabla

    
    def _resumen_libro_venta(self): 
        tabla1 = self._facturas_libro_venta()
        tabla2 = self._nc_libro_venta()
        tabla3 = self._boletas_libro_venta()
        union = pd.concat([tabla1,tabla2,tabla3])
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
        return union

    
    def _tabla_libro_venta(self,wizard=False): 
        if wizard:  
            wiz = self.search([('id','=',wizard)])
        else:
            wiz = self
        tabla1 = wiz._facturas_libro_venta()
        tabla2 = wiz._nc_libro_venta()
        tabla3 = wiz._boletas_libro_venta()
        union = pd.concat([tabla1,tabla2,tabla3])
        #if union.empty:
        # return 'error'
            #raise exceptions.Warning('No hay datos para mostrar')
        return union
    
