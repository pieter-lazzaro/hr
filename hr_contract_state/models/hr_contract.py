# -*- coding:utf-8 -*-
#
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import time

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import netsvc
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import fields, models, api


class hr_contract(models.Model):

    _name = 'hr.contract'
    _inherit = ['hr.contract', 'mail.thread']

    @api.depends('employee_id.department_id')
    def _get_department(self):

        for contract in self:
            if contract.department_id and contract.state in [
                    'pending_done', 'done'
            ]:
                contract.department_id = contract.department_id.id
            elif contract.employee_id.department_id:
                contract.department_id = contract.employee_id.department_id.id

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('trial', 'Trial'),
            ('trial_ending', 'Trial Period Ending'),
            ('open', 'Open'),
            ('contract_ending', 'Ending'),
            ('pending_done', 'Pending Termination'),
            ('done', 'Completed')
        ],
        'State',
        readonly=True,
        default='draft'
    )
    # store this field in the database and trigger a change only if the
    # contract is in the right state: we don't want future changes to an
    # employee's department to impact past contracts that have now ended.
    # Increased priority to override hr_simplify.
    department_id = fields.Many2one(
        compute='_get_department',
        obj='hr.department',
        string="Department",
        readonly=True,
        store=True,
    )
    # At contract end this field will hold the job_id, and the
    # job_id field will be set to null so that modules that
    # reference job_id don't include deactivated employees.
    end_job_id = fields.Many2one(
        'hr.job',
        'Job Title',
        readonly=True,
    )
    # The following are redefined again to make them editable only in
    # certain states
    employee_id = fields.Many2one(
        'hr.employee',
        "Employee",
        required=True,
        readonly=True,
        states={
            'draft': [('readonly', False)]
        },
    )
    type_id = fields.Many2one(
        'hr.contract.type',
        "Contract Type",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    date_start = fields.Date(
        'Start Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    wage = fields.Float(
        'Wage',
        digits=(16, 2),
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Basic Salary of the employee",
    )

    _track = {
        'state': {
            'hr_contract_state.mt_alert_trial_ending': (
                lambda self: self.state == 'trial_ending'),
            'hr_contract_state.mt_alert_open': (
                lambda self: self.state == 'open'),
            'hr_contract_state.mt_alert_contract_ending': (
                lambda self: self.state == 'contract_ending'),
        },
    }

    def _needaction_domain_get(self, cr, uid, context=None):

        users_obj = self.pool.get('res.users')
        domain = []

        if users_obj.has_group(cr, uid, 'base.group_hr_manager'):
            domain = [
                ('state', 'in', ['draft', 'contract_ending', 'trial_ending'])]
            return domain

        return False

    @api.onchange('job_id')
    def _onchange_job_id(self):

        if self.state != 'draft':
            return False
        return super(hr_contract, self)._onchange_job_id()

    @api.multi
    def condition_trial_period(self):
        self.ensure_one()

        if self.trial_date_end and self.trial_date_end > fields.Date.today():
            return True
        return False

    @api.model
    def try_ending_contracts(self):

        d = datetime.now().date() + relativedelta(days=+30)
        ending_contracts = self.search([
            ('state', '=', 'open'),
            ('date_end', '<=', fields.Date.to_string(d))
        ])

        ending_contracts.action_ending_contract()

    @api.model
    def try_contract_completed(self):
        d = datetime.now().date()
        completed_contracts = self.search([
            ('state', '=', 'open'),
            ('date_end', '<', fields.Date.to_string(d))
        ])

        completed_contracts.action_pending_done()

    @api.model
    def try_ending_trial(self):

        d = datetime.now().date() + relativedelta(days=+10)
        ending_trials = self.search([
            ('state', '=', 'trial'),
            ('trial_date_end', '<=', fields.Date.to_string(d))
        ])

        ending_trials.action_trial_ending()

    @api.model
    def try_open(self):

        d = datetime.now().date() + relativedelta(days=-5)
        trials_ended = self.search([
            ('state', '=', 'trial_ending'),
            ('trial_date_end', '<=', fields.Date.to_string(d))
        ])

        trials_ended.action_open()

    @api.multi
    def action_confirm(self):

        for contract in self:
            if contract.condition_trial_period():
                contract.state = 'trial'
            else:
                contract.state_open()


    @api.multi
    def action_ending_contract(self):
        self.write({'state': 'contract_ending'})

    @api.multi
    def action_trial(self):
        self.write({'state': 'trial'})
        return True

    @api.multi
    def action_open(self):
        self.write({'state': 'open'})
        return True

    @api.multi
    def action_pending_done(self):
        self.write({'state': 'pending_done'})
        return True

    @api.multi
    def action_done(self):
        for contract in self:
            vals = {'state': 'done',
                    'date_end': False,
                    'job_id': False,
                    'end_job_id': contract.job_id}

            if contract.date_end:
                vals['date_end'] = contract.date_end
            else:
                vals['date_end'] = fields.Datetime.now()

            self.write(vals)
        return True
