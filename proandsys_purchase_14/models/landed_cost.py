# -*- coding: utf-8 -*-

from odoo.addons.stock_landed_costs.models import stock_landed_cost
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    READONLY_STATES = {
        'done': [('readonly', True)]
    }

    folder_id = fields.Many2one('incomex.folder', 'Incomex folder')
    purchase_order_ids = fields.One2many('purchase.order', 'landed_cost_id', 'Purchase order', related='folder_id.purchase_order_ids')
    move_ids = fields.One2many('account.move', 'landed_cost_id', 'Expenses invoice')
    lines_summary_ids = fields.One2many('stock.landed.cost.lines.summary', 'cost_id', 'Lines summary',
                            copy=True, default=lambda self: self._get_default_costs(), states=READONLY_STATES)
    landed_cost_summary_ids = fields.One2many('stock.landed.cost.summary', 'cost_id', 'Landed cost summary', copy=True, states=READONLY_STATES)

    def summary_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.sent = True
        #return self.env['ir.actions.report'].report_action(self, 'proandsys_purchase_14.summary_landed_report')
        return self.env.ref('proandsys_purchase_14.summary_landedcost').report_action(self)

    def _get_default_costs(self):
        lista = []
        for product in self.env['product.product'].search([('landed_cost_ok','=',True)]):
            lista.append((0, 0, {
                'product_id': product.id,
                'split_method': 'by_current_cost_price',
                'name': product.name,
                'price_unit': 0,
                'account_id': product.property_account_expense_id.id or product.categ_id.property_account_expense_categ_id.id
            }))
        return lista

    def compute_landed_cost(self):
        self.compute_lineas()
        res =  super().compute_landed_cost()
        self.compute_summary()
        return res

    def compute_summary(self):
        dic = {}
        lista = []
        for line in self.valuation_adjustment_lines:
            if line.product_id.id not in dic.keys():
                dic[line.product_id.id] = {
                    'product_id': line.product_id.id,
                    'quantity': 0.0,
                    'former_cost': 0.0,
                    'cost_id': self.id,
                    'former_stock_cost': 0.0,
                    'former_stock_quantity': 0.0,
                    'additional_landed_cost': 0.0
                }
            dic[line.product_id.id]['additional_landed_cost'] += line.additional_landed_cost
            dic[line.product_id.id]['quantity'] += line.quantity
            dic[line.product_id.id]['former_cost'] += line.former_cost
            dic[line.product_id.id]['former_stock_quantity'] += line.former_stock_quantity
            dic[line.product_id.id]['former_stock_cost'] += line.former_stock_cost
        if dic:
            self.write({'landed_cost_summary_ids': [(5, 0, 0)]})
            for key,value in dic.items():
                lista += [(0, 0, value)]
            self.landed_cost_summary_ids = lista
        return True

    def _create_accounting_entries(self, move, qty_out):
        if not qty_out:
            qty_out = line.former_stock_quantity - line.product_id.qty_available
        return super()._create_accounting_entries(move, qty_out)

    def button_validate(self):
        res = super().button_validate()
        for cost in self:
            for line in cost.landed_cost_summary_ids:
            ########################################### Aqui corregir #############################################
                line.product_id.standard_price = line.final_stock_cost_per_unit
            #######################################################################################################
        return res

    def compute_lineas(self): 
        dic = {}
        if self.lines_summary_ids:
            dic['name'] = 'COSTEO IMPORTACION'
            dic['cost_id'] = self.lines_summary_ids[0].cost_id.id
            dic['product_id'] = self.lines_summary_ids[0].product_id.id
            dic['price_unit'] = sum([a.price_unit for a in self.lines_summary_ids])
            dic['split_method'] = self.lines_summary_ids[0].split_method
            dic['account_id'] = self.lines_summary_ids[0].account_id.id
        if dic:
            self.write({'cost_lines': [(5,0,0)]})
            self.cost_lines.create(dic)
        return True

    def _compute_product_new_cost(self, product_id):
        quant_obj = self.env['stock.quant']
        current_value = 0.0
        quants = quant_obj.search([('product_id','=',product_id.id),('location_id.usage','=','internal')])
        for quant in quants:
            current_value += quant.cost
        return current_value

    def get_valuation_lines(self):
        lines = super().get_valuation_lines()
        for line in lines:
            producto = self.env['product.product'].search([('id','=',line['product_id'])])
            fecha = self.env['stock.move'].browse(line['move_id']).date
            domain = [('product_id','=',producto.id),('state','=','done'),('location_id.usage','not in',['internal','transit']),('location_dest_id.usage','in',['internal','transit']),('date','<=',fecha)]
            entradas = self.env['stock.move'].search(domain)
            salidas = self.env['stock.move'].search(domain)
            cant_entrada = 0
            cant_salida = 0
            if entradas:
                cant_entrada = sum([move.product_qty for move in entradas] or 0)
            if salidas:
                cant_salida = sum([move.product_qty for move in salidas] or 0)
            cant = (cant_entrada-cant_salida)
            line['former_stock_quantity'] = cant
            line['former_stock_cost'] = producto.standard_price * cant
            line['former_stock_cost_per_unit'] = producto.standard_price

        return lines

class SummaryLandedCost(models.Model):
    _name = 'stock.landed.cost.summary'
    _description = "Landed Cost"

    name = fields.Char('Description', related='cost_id.name', store=True)
    cost_id = fields.Many2one('stock.landed.cost', 'Landed cost', ondelete='cascade', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='cost_id.currency_id')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    quantity = fields.Float('Quantity purchased', default=1.0, digits='Product Unit of Measure', required=True)
    weight = fields.Float('Weight', default=1.0, digits='Product Unit of Measure')
    volume = fields.Float('Volume', default=1.0, digits='Product Unit of Measure')
    former_cost = fields.Monetary('Old total cost')
    # former_purchase_cost = fields.Float('Costo original')
    former_cost_per_unit = fields.Monetary('Old unitary cost', compute='_compute_costs', store=True)
    additional_landed_cost = fields.Monetary('Aditional landed cost')
    final_cost = fields.Monetary('Final cost', compute='_compute_costs', store=True)
    final_cost_per_unit = fields.Monetary('New unitary cost', compute='_compute_costs', store=True)
    former_stock_quantity = fields.Float('Original stock quantity')
    former_stock_cost = fields.Float('Original total stock cost')
    former_stock_cost_per_unit = fields.Monetary('Original unitary stock cost', compute='_compute_costs', store=True)
    final_stock_cost = fields.Monetary('Final stock cost', compute='_compute_costs', store=True)
    final_stock_cost_per_unit = fields.Monetary('New unitary stock cost', compute='_compute_costs', store=True)

    @api.depends('former_cost', 'quantity','additional_landed_cost','former_stock_cost','former_stock_quantity')
    def _compute_costs(self):
        for record in self:
            record.former_cost_per_unit = record.former_cost / (record.quantity or 1.0)
            record.final_cost = record.former_cost + record.additional_landed_cost
            record.final_cost_per_unit = (record.former_cost + record.additional_landed_cost) / (record.quantity or 1.0)
            record.former_stock_cost_per_unit = record.former_stock_cost / (record.former_stock_quantity or 1.0)
            record.final_stock_cost = record.former_stock_cost + record.additional_landed_cost
            record.final_stock_cost_per_unit = (record.former_stock_cost + record.additional_landed_cost) / (record.former_stock_quantity or 1.0)

class LandedCostLineSummary(models.Model):
    _name = 'stock.landed.cost.lines.summary'
    _description = 'Stock Landed Cost Lines Summary'

    cost_id = fields.Many2one('stock.landed.cost', 'Landed Cost', ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated','=',False)])
    name = fields.Char('Description')
    price_unit = fields.Float('Cost', digits='Costo', required=True)
    split_method = fields.Selection(stock_landed_cost.SPLIT_METHOD, 'Split Method', required=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name or ''
            self.price_unit = self.product_id.standard_price or 0.0
            self.account_id = self.product_id.property_account_expense_id.id or self.product_id.categ_id.property_account_expense_categ_id.id
        else:
            self.quantity = 0.0
            self.price_unit = 0.0

        self.split_method = self.split_method or 'equal'

class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'
    
    former_stock_quantity = fields.Float('Original stock quantity')
    former_stock_cost = fields.Float('Original total stock cost')
    former_stock_cost_per_unit = fields.Float('Original unitary stock cost')
    final_stock_cost = fields.Float('Final stock cost')
    final_stock_cost_per_unit = fields.Float('New unitary stock cost')

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
        """
        Generate the account.move.line values to track the landed cost.
        Afterwards, for the goods that are already out of stock, we should create the out moves
        """
        AccountMoveLine = []

        base_line = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': self.quantity, #Modificado, era 0
        }
        debit_line = dict(base_line, account_id=debit_account_id)
        credit_line = dict(base_line, account_id=credit_account_id)
        diff = self.additional_landed_cost
        if diff > 0:
            debit_line['debit'] = diff
            credit_line['credit'] = diff
        else:
            # negative cost, reverse the entry
            debit_line['credit'] = -diff
            credit_line['debit'] = -diff
        AccountMoveLine.append([0, 0, debit_line])
        AccountMoveLine.append([0, 0, credit_line])

        # Create account move lines for quants already out of stock
        if qty_out > 0:
            debit_line = dict(base_line,
                              name=(self.name + ": " + str(qty_out) + _(' already out')),
                              quantity=qty_out, #Modificado, era 0
                              account_id=already_out_account_id)
            credit_line = dict(base_line,
                               name=(self.name + ": " + str(qty_out) + _(' already out')),
                               quantity=qty_out, #Modificado, era 0
                               account_id=debit_account_id)
            diff = diff * qty_out / (self.former_stock_quantity or 1.0) #Modificado, era "/ self.quantity"
            if diff > 0:
                debit_line['debit'] = diff
                credit_line['credit'] = diff
            else:
                # negative cost, reverse the entry
                debit_line['credit'] = -diff
                credit_line['debit'] = -diff
            AccountMoveLine.append([0, 0, debit_line])
            AccountMoveLine.append([0, 0, credit_line])

            if self.env.company.anglo_saxon_accounting:
                expense_account_id = self.product_id.product_tmpl_id.get_product_accounts()['expense'].id
                debit_line = dict(base_line,
                                  name=(self.name + ": " + str(qty_out) + _(' already out')),
                                  quantity=qty_out, #Modificado, era 0
                                  account_id=expense_account_id)
                credit_line = dict(base_line,
                                   name=(self.name + ": " + str(qty_out) + _(' already out')),
                                   quantity=qty_out, #Modificado, era 0
                                   account_id=already_out_account_id)

                if diff > 0:
                    debit_line['debit'] = diff
                    credit_line['credit'] = diff
                else:
                    # negative cost, reverse the entry
                    debit_line['credit'] = -diff
                    credit_line['debit'] = -diff
                AccountMoveLine.append([0, 0, debit_line])
                AccountMoveLine.append([0, 0, credit_line])
        return AccountMoveLine

class CarpetaImportacion(models.Model):
    _inherit = 'incomex.folder'

    landed_cost_ids = fields.One2many('stock.landed.cost', 'folder_id', 'Landed Cost')

