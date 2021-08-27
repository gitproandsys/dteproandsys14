from odoo import models, fields, api, http
from datetime import date
from dateutil.relativedelta import relativedelta
import xlsxwriter
from odoo.http import request, Response
from odoo.addons.web.controllers.main import serialize_exception,content_disposition

from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class wizard_proandsys_reportes_chile_14(models.TransientModel):
    _name = 'wizard.reportes.chile'

    informe = fields.Selection([
        ('Cuenta Corriente','Cuenta Corriente por Empresa'), 
        ('Libro de Ventas','Libro de Ventas'),
        ('Libro de Compras','Libro de Compras'), 
        ('Libro de Honorarios','Libro de Honorarios'),
        ('Balance Tributario','Balance Tributario'),
        ('Libro Diario','Libro Diario'),
        ('Libro Mayor','Libro Mayor'),
        ], 'Tipo de informe', required=True)
    arbol_id = fields.Many2one('account.account')
    fecha_inicio = fields.Date('Fecha de inicio', default=date.today().replace(day=1))  
    fecha_term = fields.Date('Fecha de termino', 
        default=date.today().replace(day=1)+relativedelta(months=1, days=-1)) 
    partner_ids = fields.Many2many('res.partner')
    acount_ids = fields.Many2many('account.account')
    pendiente = fields.Boolean('Pendientes', default=True)     
    file = fields.Binary(readonly=True)
    filename = fields.Char() 
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)
    section_id = fields.Many2one('crm.case.section')
    cabezera = fields.Boolean('Imprimir Cabezera', default=True)
    
    def _get_domain(self):
        search_domain=[]
        search_domain += [('company_id','=',self.company_id.id)]
        search_domain += [('date', '>=', self.fecha_inicio)]
        search_domain += [('date', '<=', self.fecha_term)]             
        if self.partner_ids:
            search_domain+=[('partner_id', 'in', self.partner_ids.ids)]              
        if self.section_id:
            search_domain += [('section_id','=', self.section_id.id)]         
        return search_domain  

    
    def imprimir_pdf(self):        
        if self.informe=='Cuenta Corriente':
            report_name='proandsys_reportes_chile_14.fact_abiertas'
        elif self.informe=='Libro de Ventas':
            report_name='proandsys_reportes_chile_14.libro_venta'
        elif self.informe=='Libro de Compras':
            report_name='proandsys_reportes_chile_14.libro_compra'
        elif self.informe=='Libro de Guias':
            report_name='proandsys_reportes_chile_14.libro_guia'
        elif self.informe=='Libro de Honorarios':
            report_name='proandsys_reportes_chile_14.libro_honorario'
        elif self.informe=='Libro Diario':
            report_name='proandsys_reportes_chile_14.libro_diario'
        elif self.informe=='Libro Mayor':
            report_name='proandsys_reportes_chile_14.libro_mayor'
        try:
            informe = self.env.ref(report_name).report_action(self)   
        except:                          
            informe = self.env['ir.actions.report'].report_action(self, report_name)
        return informe

    
    def imprimir_excel(self):             
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/get_excel?informe=%s&wizard=%s'% (self.informe, self.id),
            'target': 'self'            
        }

    
    def _excel_file(self,tabla,nombre):        
        data2 = BytesIO()        
        workbook = xlsxwriter.Workbook(data2, {'in_memory': True})      
        datos = tabla
        worksheet2 = workbook.add_worksheet(nombre)
        worksheet2.set_column('A:Z', 20)     
        columnas = list(datos.columns.values)        
        columns2 = [{'header':r} for r in columnas]
        columns2[0].update({'total_string': 'Total'})
        currency_format = workbook.add_format({'num_format': '#,##0'})
        for record in columns2[1:]:
            record.update({'total_function': 'sum','format': currency_format})
        data = datos.values.tolist()
        col3 = len(columns2)-1
        col2=len(data)+1
        cells = xlsxwriter.utility.xl_range(0,0,col2,col3)
        worksheet2.add_table(cells, {'data': data, 'total_row': 1, 'columns':columns2})

        workbook.close()        
        data2 = data2.getvalue()         
        return data2 

class wizard_proandsys_reportes_chile_14_excel(models.TransientModel):
    _name = 'wizard.reportes.chile.excel'
    file = fields.Binary()
    filename = fields.Char()

class libro_ventas_tax_inherit(models.Model):
    _inherit = 'account.tax'
    mostrar_v = fields.Boolean('Mostrar en libro de venta')  
    mostrar_c = fields.Boolean('Mostrar en libro de compra')

class proandsys_reportes_chile_14_controlador(http.Controller):

    @http.route('/web/get_excel', type='http', auth="user")
    @serialize_exception
    def download_document(self,informe,wizard,debug=0): 
        filecontent = ''
        report_obj = request.env['wizard.reportes.chile']        
        if informe=='Cuenta Corriente':
            tabla = report_obj._facturas_abiertas(int(wizard)) 
            nombre = 'Informe Cuenta Corriente'            
        if informe=='Libro de Ventas':
            tabla = report_obj._tabla_libro_venta(int(wizard))          
            nombre = 'Libro de Ventas'            
        if informe=='Libro de Compras':
            tabla = report_obj._tabla_libro_compra(int(wizard))
            nombre = 'Libro de Compras'            
        if informe=='Libro de Guias':
            tabla = report_obj._libro_guias(int(wizard)) 
            nombre = 'Libro de Guias'            
        if informe=='Libro de Honorarios':
            tabla = report_obj._libro_honorarios(int(wizard)) 
            nombre = 'Libro de Honorarios'                      
        if informe=='Libro Diario':
            tabla = report_obj._libro_diario(int(wizard))
            nombre = 'Libro Diario'  
        if informe=='Libro Mayor':
            tabla = report_obj._libro_mayor_sql(int(wizard)) 
            nombre = 'Libro Mayor'            
        if not tabla.empty and nombre:      
            filecontent = report_obj._excel_file(tabla,nombre)
        if not filecontent:
            return Response("No hay datos para mostrar",content_type='text/html;charset=utf-8',status=500)           
        return request.make_response(filecontent,
        [('Content-Type', 'application/pdf'), ('Content-Length', len(filecontent)),
        ('Content-Disposition', content_disposition(nombre+'.xlsx'))])