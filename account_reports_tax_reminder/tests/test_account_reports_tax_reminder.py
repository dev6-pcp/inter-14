# -*- coding: utf-8 -*-
from datetime import date, timedelta
from unittest.mock import patch

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestAccountReportsTaxReminder(TestAccountReportsCommon):

    def setUp(self):
        super().setUp()

        self.tax_return_move = self.env['account.move'].search([
            ('tax_closing_end_date', '!=', False),
            ('state', '=', 'draft'),
            ('company_id', '=', self.company_data['company'].id),
        ])

        # Force the closing end date in the past to avoid an error
        today = date.today()
        end_of_last_month = today + timedelta(days=-today.day)
        self.tax_return_move.write({
            'date': end_of_last_month,
            'tax_closing_end_date': end_of_last_month,
        })

        self.move_sale = self.env['account.move'].create({
            'move_type': 'entry',
            'date': end_of_last_month,
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {
                    'debit': 1120.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 120.0,
                    'account_id': self.company_data['default_account_tax_sale'].id,
                    'tax_repartition_line_id': self.company_data['company'].account_sale_tax_id.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 1000.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        self.move_sale.action_post()

    def test_posting_adds_a_reminder(self):
        ''' Test that posting the tax report move adds a reminder activity
        '''
        reminder_mat_id = self.env.ref('account_reports_tax_reminder.mail_activity_type_tax_report_to_be_sent')
        reminder_ma_domain = [
            ('res_model', '=', self.tax_return_move._name),
            ('res_id', '=', self.tax_return_move.id),
            ('activity_type_id', '=', reminder_mat_id.id),
        ]

        # Refreshing the tax entry should not post any mail activity of this type
        self.tax_return_move.refresh_tax_entry()

        self.assertRecordValues(self.tax_return_move, [{'state': 'draft'}])
        reminder_id = self.env['mail.activity'].search(reminder_ma_domain)
        self.assertEqual(len(reminder_id), 0)

        # Posting the tax entry should post one mail activity of this type
        report = self.env['account.generic.tax.report']
        with patch.object(type(report), 'get_pdf', autospec=True, side_effect=lambda *args, **kwargs: b''):
            self.tax_return_move.action_post()

        self.assertRecordValues(self.tax_return_move, [{'state': 'posted'}])

        reminder_id = self.env['mail.activity'].search(reminder_ma_domain)
        self.assertRecordValues(reminder_id, [{
            'summary': 'Tax report is ready to be sent to the administration',
            'date_deadline': fields.Date.context_today(self.env.user),
            'force_next': False,
        }])
