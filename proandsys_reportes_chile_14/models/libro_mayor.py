from odoo import models, fields, api, exceptions
from datetime import date,datetime
from dateutil.relativedelta import relativedelta
from collections import OrderedDict
import pandas as pd
import logging

_logger = logging.getLogger(__name__)


class libro_mayor_proandsys_reportes_chile_14(models.TransientModel):
    _inherit = 'wizard.reportes.chile' 
    
    
    def dic_libro_mayor(self):
        dic = OrderedDict([
                ('Fecha',''),
                ('Comprobante',''),
                ('Rut',''),
                ('Partner',''),
                ('Cuenta',''),
                ('Glosa',''),
                ('Documento',''),
                ('Debe',0.0),
                ('Haber',0.0),        
                ('Saldo',0.0)         
                ])
        return dic

    
    def _libro_mayor_sql(self,wizard=False):
        if wizard:  
            wiz = self.search([('id','=',wizard)])
        else:
            wiz = self
        company = wiz.company_id.id
        #if not (wiz.fecha_inicio or wiz.fecha_term):
        #    raise exceptions.Warning('Debe seleccionar al menos un periodo')
        #periodo = wiz.period_ids[0]
        fecha_inicio = wiz.fecha_inicio
        fecha_term = wiz.fecha_term
        #fiscal = periodo.fiscalyear_id.id
        #perids = set(wiz.period_ids.ids)
        #periodos= '('+",".join(map(str,perids))+')'
        cuentas = ''
        if wiz.acount_ids:
            cuentas = 'and aa.id in ('+",".join(map(str,set(wiz.acount_ids.ids)))+')'
        wiz.env.cr.execute("""
            SELECT  
            null as Fecha,
            'Saldo Inicial' as comprobante,
            null,
            null,          
            concat_ws(' - ', aa.code::text, aa.name::text) as cuenta,   
            null,
            null,        
            sum(aml.debit),
            sum(aml.credit)

            FROM 
            account_move_line aml,
            account_account aa,
            account_move am          

            WHERE   
            aml.account_id=aa.id and
            aml.move_id=am.id and 
            am.state='posted' and 
            aml.company_id = %s and             
            aml.date <= '%s'            
            %s

            GROUP BY
            cuenta

            UNION ALL

            SELECT
            q1.fecha,
            q1.comprobante,
            q2.vat,
            q2.partner,
            q1.cuenta,
            q1.ref,
            q1.nombre,
            q1.debit,
            q1.credit

            FROM
            (
            SELECT

            aml.date as fecha,
            am.name as comprobante,
            concat_ws(' - ', aa.code::text, aa.name::text) as cuenta,
            aml.ref as ref,
            aml.name as nombre,
            aml.debit as debit,
            aml.credit as credit,
            aml.partner_id as partner_id

            FROM 
            account_move_line aml,
            account_account aa,
            account_move am

            WHERE   
            aml.account_id=aa.id and
            aml.move_id=am.id and 
            am.state='posted' and
            aml.company_id = %s and
            aml.date >= '%s' and
            aml.date <= '%s'            
            %s
            )q1

            LEFT JOIN

            (
            SELECT

            rp.id id,
            rp.vat rut,
            rp.name partner

            FROM

            res_partner rp
            )q2

            ON
            q2.id=q1.partner_id

            ORDER BY
            cuenta, fecha NULLS FIRST, comprobante                       
            """ %(company,fecha_inicio,cuentas,company,fecha_inicio,fecha_term,cuentas))
        dic = wiz.dic_libro_mayor()
        lista = []
        docs = wiz.env.cr.fetchall()        
        # cuentas = set([(record[9],record[4]) for record in docs])
        # for record in cuentas:
        #     lista += wiz._libro_mayor_saldo_inicial_sql(record[0],record[1])
        for record in docs:
            dicti = OrderedDict()
            dicti.update(dic)
            dicti['Fecha']=record[0]
            dicti['Comprobante']=record[1]
            dicti['Rut']=record[2]
            dicti['Partner']=record[3]
            dicti['Cuenta']=record[4]
            dicti['Glosa']=record[5]
            dicti['Documento']=record[6]
            dicti['Debe']=float(record[7])
            dicti['Haber']=float(record[8])
            lista.append(dicti)            
        tabla = pd.DataFrame(lista) 
        if not tabla.empty:
            tabla['Saldo'] = (tabla['Debe']-tabla['Haber'])   
            tabla['Saldo'] = tabla.groupby('Cuenta')['Saldo'].transform(pd.Series.cumsum) 
        return tabla

    
