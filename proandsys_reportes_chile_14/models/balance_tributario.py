from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class WizardReportesChileBalance(models.TransientModel):
    _inherit = 'wizard.reportes.chile'  

    fy_start_date = fields.Date(compute='_compute_fy_start_date')

    unaffected_earnings_account = fields.Many2one(comodel_name="account.account", compute="_compute_unaffected_earnings_account", store=True, )

    @api.depends('fecha_inicio')
    def _compute_fy_start_date(self):
        for wiz in self.filtered('fecha_inicio'):
            date = fields.Datetime.from_string(wiz.fecha_inicio)
            res = self.company_id.compute_fiscalyear_dates(date)
            wiz.fy_start_date = res['date_from']

    @api.depends("company_id")
    def _compute_unaffected_earnings_account(self):
        account_type = self.env.ref("account.data_unaffected_earnings")
        for record in self:
            record.unaffected_earnings_account = self.env["account.account"].search(
                [
                    ("user_type_id", "=", account_type.id),
                    ("company_id", "=", record.company_id.id),
                ]
            )

    def create_trial_balance_wizard(self):
        data = {
                "date_from": self.fecha_inicio,
                "date_to": self.fecha_term,
                "target_move": "posted",
                "hide_account_at_0": True,
                "foreign_currency": False,
                "company_id": self.company_id.id,
                "account_ids": [],
                "partner_ids": [],
                "journal_ids": [],
                "fy_start_date": self.fy_start_date,
                "show_partner_details": False,
                "hierarchy_on": 'none',
                "limit_hierarchy_level": False,
                "show_hierarchy_level": False,
                "hide_parent_hierarchy_level": False,
                "unaffected_earnings_account": self.unaffected_earnings_account.id,
            }
        trial_balance_report_wizard_id = self.env["trial.balance.report.wizard"].create(data)
        return trial_balance_report_wizard_id

    def button_export_pdf(self):
        self.ensure_one()
        report_type = 'qweb-pdf'
        return self.create_trial_balance_wizard().with_context({'proandsys_reportes_chile_14':True})._export(report_type)

    def button_export_xlsx(self):
        self.ensure_one()
        report_type = "xlsx"
        return self.create_trial_balance_wizard().with_context({'proandsys_reportes_chile_14':True})._export(report_type)

class TrialBalanceReportWizard(models.TransientModel):

    _inherit = "trial.balance.report.wizard"
    
    def _export(self, report_type):
        """Default export is PDF."""
        proandsys_reportes_chile_14 = self._context.get('proandsys_reportes_chile_14')
        if proandsys_reportes_chile_14:
            return self._print_report_opendrive(report_type)
        return self._print_report(report_type)

    def _print_report_opendrive(self, report_type):
        self.ensure_one()
        data = self._prepare_report_trial_balance()
        if report_type == "xlsx":
            report_name = "proandsys_reportes_chile_14.report_tbx"
        else:
            report_name = "proandsys_reportes_chile_14.trial_balance"
        return (
            self.env["ir.actions.report"]
            .search(
                [("report_name", "=", report_name), ("report_type", "=", report_type)],
                limit=1,
            )
            .report_action(self, data=data)
        )

class TrialBalanceReport(models.AbstractModel):
    _inherit = "report.account_financial_report.trial_balance"
    _name = "report.proandsys_reportes_chile_14.trial_balance"
