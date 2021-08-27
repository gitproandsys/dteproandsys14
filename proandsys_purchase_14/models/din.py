# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning
import odoo.addons.decimal_precision as dp


class AccountDin(models.Model):
    _name = 'account.din'
    _description = "Account DIN"
    _inherit = ['mail.thread']

    EDITABLE_STATES = {
        'draft': [('readonly', False)]
    }

    @api.model
    def _get_default_journal(self):
        domain = [('company_id','=',self.env.user.company_id.id)]
        return self.env['account.journal'].search(domain, limit=1)

    name = fields.Char('Name', readonly=True, copy=False, related='origin')
    partner_id = fields.Many2one('res.partner', 'Custom', required=True, readonly=True, states=EDITABLE_STATES)
    account_id = fields.Many2one('account.account', 'Account', required=True, readonly=True, states=EDITABLE_STATES)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True, default=_get_default_journal,
                            domain="[('company_id','=',company_id)]", readonly=True, states=EDITABLE_STATES)
    currency_id = fields.Many2one('res.currency', 'Currency', related='journal_id.currency_id', required=True, readonly=True)
    origin = fields.Char('Number', required=True, readonly=True, states=EDITABLE_STATES)
    date = fields.Date('Post Date', required=True, readonly=True, states=EDITABLE_STATES)
    date_din = fields.Date('date', required=True, readonly=True, states=EDITABLE_STATES)
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True, index=True,
                    ondelete='restrict', help='Link to the automatically generated Journal Items.')
    rate = fields.Float('Rate', digits='Account', required=True, readonly=True, states=EDITABLE_STATES)
    cif_amount = fields.Monetary('CIF Amount', required=True, readonly=True, states=EDITABLE_STATES)
    ad_valorem = fields.Monetary('Ad Valorem', readonly=True, states=EDITABLE_STATES)
    account_ad_valorem_id = fields.Many2one('account.account', 'Ad Valorem Account', readonly=True, states=EDITABLE_STATES)
    others_1 = fields.Monetary('Others 1', readonly=True, states=EDITABLE_STATES)
    account_others_1_id = fields.Many2one('account.account', 'Others 1 Account', readonly=True,
                            domain="[('internal_type','!=','view')]", states=EDITABLE_STATES)
    others_2 = fields.Monetary('Others 2', readonly=True, states=EDITABLE_STATES)
    account_others_2_id = fields.Many2one('account.account', 'Others 2 Account',
                    domain="[('internal_type','!=','view')]", readonly=True, states=EDITABLE_STATES)
    others_3 = fields.Monetary('Others 3', readonly=True, states=EDITABLE_STATES)
    account_others_3_id = fields.Many2one('account.account', 'Others 3 Account',
                    domain="[('internal_type','!=','view')]", readonly=True, states=EDITABLE_STATES)
    others_4 = fields.Monetary('Others 4', readonly=True, states=EDITABLE_STATES)
    account_others_4_id = fields.Many2one('account.account', 'Others 4 Account',
                    domain="[('internal_type','!=','view')]", readonly=True, states=EDITABLE_STATES)
    amount_no_tax_usd = fields.Monetary('Other Expenses No Tax USD', readonly=True, states=EDITABLE_STATES)
    account_no_tax_id = fields.Many2one('account.account', 'Other Expenses No Tax Account', readonly=True,
                                            domain="[('internal_type','!=','view')]", states=EDITABLE_STATES)
    diff_tax = fields.Monetary('IVA difference (CLP)', readonly=True, states=EDITABLE_STATES)
    tax_id = fields.Many2one('account.tax', 'Tax', domain="[('type_tax_use','=','purchase')]",
                                 required=True, copy=True, readonly=True, states=EDITABLE_STATES)
    total_untaxed = fields.Monetary('Amount untaxed', store=True, compute='_compute_amount')
    amount_tax = fields.Monetary('IVA', store=True, compute='_compute_amount')
    amount_total = fields.Monetary('Total', store=True, compute='_compute_amount')
    create_uid = fields.Many2one('res.users', 'User', default=lambda self: self._uid, copy=False)
    folder_id = fields.Many2one('incomex.folder', 'Related incomex folder', readonly=True, states=EDITABLE_STATES)
    notes = fields.Text('Notes', readonly=True, states=EDITABLE_STATES)
    company_id = fields.Many2one('res.company', 'Company', change_default=True, required=True,
                        readonly=True, states=EDITABLE_STATES, default=lambda self: self.env.company)
    state = fields.Selection([('draft','Draft'),('done','Done')], 'State', default='draft', track_visibility='onchange', copy=False)

    @api.depends('rate','cif_amount','ad_valorem','others_1','others_2','others_3','others_4','tax_id','diff_tax')
    def _compute_amount(self):
        tax_sum = 0
        amount_untaxed = self.rate * (self.cif_amount + self.ad_valorem + self.others_1 + self.others_2 + self.others_3 + self.others_4)
        taxs = self.tax_id.compute_all(amount_untaxed, self.env.user.company_id.currency_id, partner=self.partner_id)
        if 'taxes' in taxs:
            for tax in taxs['taxes']:
                tax_sum += tax['amount']
        self.total_untaxed = round(amount_untaxed, 0)
        self.amount_tax = round(tax_sum + self.diff_tax, 0)
        self.amount_total = round(taxs['total_included'] + self.diff_tax if 'total_included' in taxs else 0, 0)

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self): 
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
        if p:
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            self.update({
                'account_id': pay_account.id,
            })

    @api.onchange('ad_valorem','others_1','others_2','others_3','others_4','amount_no_tax_usd')
    def onchange_account_values(self):
        if not self.ad_valorem:
            self.account_ad_valorem_id = None
        if not self.others_1:
            self.account_others_1_id = None
        if not self.others_2:
            self.account_others_2_id = None
        if not self.others_3:
            self.account_others_3_id = None
        if not self.others_4:
            self.account_others_4_id = None
        if not self.amount_no_tax_usd:
            self.account_no_tax_id = None

    def button_dummy(self):
        return True

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('No se puede borrar una Decaracion contabilizada')
            else:
                return super(AccountDin, self).unlink()

    def _get_line_values(self, din, account_id, debit=0.0, credit=0.0):
        return {
            'name': din.origin,
            'date': fields.Date.context_today(self),
            'partner_id': din.partner_id.id,
            'account_id': account_id,
            'journal_id': din.journal_id.id,
            'debit': debit,
            'credit': credit
        }

    def _get_move_vals(self, din, lines):
        return {
            'ref': din.origin,
            'journal_id': din.journal_id.id,
            'currency_id': din.journal_id.currency_id.id or din.company_id.currency_id.id,
            'date': din.date,
            'narration': din.notes,
            'din_id': din.id,
            'company_id': din.company_id.id,
            'line_ids': lines
        }

    def din_open(self):
        account_move = self.env['account.move']
        obj_sequence = self.env['ir.sequence']

        for din in self:
            if not din.tax_id.invoice_repartition_line_ids.filtered(lambda l: l.account_id):
                raise UserError(_('You need to set the Invoice Tax Account to the selected tax'))

            ctx = dict(self._context, lang=din.partner_id.lang)
            tax_account_id = [line.account_id for line in din.tax_id.invoice_repartition_line_ids.filtered(lambda l: l.account_id)][0]
            creditos = round(din.amount_tax) + round(din.rate * din.ad_valorem) + round(din.rate * din.others_1) + \
                        round(din.rate * din.others_2) + round(din.rate * din.others_3) + round(din.rate * din.others_4) + round(din.rate * din.amount_no_tax_usd)
            debitos = round(din.amount_tax)

            lines = [(0, 0, self._get_line_values(din, din.account_id.id, credit=creditos)),
                (0, 0, self._get_line_values(din, tax_account_id.id, debit=debitos))]

            if din.ad_valorem and din.account_ad_valorem_id:
                lines.append((0, 0, self._get_line_values(din, din.account_ad_valorem_id.id, debit=round(din.ad_valorem * din.rate))))

            if din.others_1 and din.account_others_1_id:
                lines.append((0, 0, self._get_line_values(din, din.account_others_1_id.id, debit=round(din.others_1 * din.rate))))

            if din.others_2 and din.account_others_2_id:
                lines.append((0, 0, self._get_line_values(din, din.account_others_2_id.id, debit=round(din.others_2 * din.rate))))

            if din.others_3 and din.account_others_3_id:
                lines.append((0, 0, self._get_line_values(din, din.account_others_3_id.id, debit=round(din.others_3 * din.rate))))

            if din.others_4 and din.account_others_4_id:
                lines.append((0, 0, self._get_line_values(din, din.account_others_4_id.id, debit=round(din.others_4 * din.rate))))

            if din.account_no_tax_id and din.amount_no_tax_usd:
                lines.append((0, 0, self._get_line_values(din, din.account_no_tax_id.id, debit=round(din.amount_no_tax_usd * din.rate))))

            move = account_move.with_context(ctx).create(self._get_move_vals(din, lines))
            move.action_post()

            din.with_context(ctx).write({
                'move_id': move.id,
                'state': 'done',
                'name': din.name if din.name else obj_sequence.get('account.din')
            })

        return True

    def din_cancel(self):
        for record in self:
            return record.with_context({'force_delete':True})._din_cancel()

    def _din_cancel(self):
        moves = self.env['account.move']
        for din in self:
            if din.move_id:
                moves += din.move_id
            for line in din.move_id.line_ids:
                if line.full_reconcile_id:
                    raise UserError(_('You cannot cancel an invoice which is partially paid. '+\
                                    'You need to unreconcile related payment entries first.'))
        # First, set the din as draft and detach the move ids
        self.write({'state': 'draft', 'move_id': False})
        if moves:
            # second, invalidate the move(s)
            moves.button_cancel()
            # delete the move this din was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            moves.unlink()
        return True

