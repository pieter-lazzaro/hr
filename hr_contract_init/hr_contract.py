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

from datetime import datetime, timedelta

from odoo import netsvc
from odoo.addons import decimal_precision as dp
from odoo import fields, models, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from odoo.tools.translate import _
from odoo.exceptions import UserError

class contract_init(models.Model):

    _name = 'hr.contract.init'
    _description = 'Initial Contract Settings'

    _inherit = 'ir.needaction_mixin'

    # Return records with latest date first
    _order = 'date desc'

    name = fields.Char(
        'Name',
        size=64,
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    date = fields.Date(
        'Effective Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    wage_ids = fields.One2many(
        'hr.contract.init.wage',
        'contract_init_id',
        'Starting Wages', readonly=True,
        states={'draft': [('readonly', False)]},
    )
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        'Payroll Structure',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    trial_period = fields.Integer(
        'Trial Period',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Length of Trial Period, in days",
        default=0
    )
    active = fields.Boolean(
        'Active',
        default=True
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('approve', 'Approved'),
            ('decline', 'Declined'),
        ],
        'State',
        default='draft',
        readonly=True,
    )


    def _needaction_domain_get(self, cr, uid, context=None):

        users_obj = self.pool.get('res.users')

        if users_obj.has_group(cr, uid, 'base.group_hr_director'):
            domain = [('state', 'in', ['draft'])]
            return domain

        return False

    @api.multi
    def unlink(self):

        for record in self:
            if record.state in ['approve', 'decline']:
                raise UserError(_('You may not a delete a record that is not in a '
                                  '"Draft" state'))

        return super(contract_init, self).unlink()

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})

    @api.multi
    def action_approve(self):
        self.write({'state': 'approve'})

    def action_decline(self):
        self.write({'state': 'decline'})


class init_wage(models.Model):

    _name = 'hr.contract.init.wage'
    _description = 'Starting Wages'

    job_id = fields.Many2one(
        'hr.job',
        'Job',
    )
    starting_wage = fields.Float(
        'Starting Wage',
        digits=dp.get_precision('Payroll'),
        required=True
    )
    is_default = fields.Boolean(
        'Use as Default',
        help="Use as default wage",
    )
    contract_init_id = fields.Many2one(
        'hr.contract.init',
        'Contract Settings',
    )
    category_ids = fields.Many2many(
        'hr.employee.category',
        'contract_init_category_rel',
        'contract_init_id',
        'category_id',
        'Tags',
    )


    def _rec_message(self):
        return _('A Job Position cannot be referenced more than once in a '
                 'Contract Settings record.')

    _sql_constraints = [
        ('unique_job_cinit', 'UNIQUE(job_id,contract_init_id)', lambda self: self._rec_message()),
    ]

    @api.multi
    def unlink(self):
        for record in self:
            if not record.contract_init_id:
                continue

            if record.contract_init_id.state in ['approve', 'decline']:
                raise UserError(
                    _('You may not a delete a record that is not in a '
                      '"Draft" state')
                )

        return super(init_wage, self).unlink()


class hr_contract(models.Model):

    _inherit = 'hr.contract'

    @api.model
    def _default_get_wage(self, job_id=None):
        ''' Returns the wage for job with id job_id. '''
        res = 0
        default = 0
        init = self.get_latest_initial_values()

        if job_id:
            catdata = self.env['hr.job'].read(['category_ids'])
        else:
            catdata = False

        if init is not None:
            for line in init.wage_ids:
                if job_id is not None and line.job_id.id == job_id:
                    res = line.starting_wage
                elif catdata:
                    cat_id = False
                    category_ids = [c.id for c in line.category_ids]
                    for ci in catdata['category_ids']:
                        if ci in category_ids:
                            cat_id = ci
                            break
                    if cat_id:
                        res = line.starting_wage
                if line.is_default and default == 0:
                    default = line.starting_wage
                if res != 0:
                    break
        if res == 0:
            res = default
        return res

    @api.model
    def _default_get_struct(self):

        res = False
        init = self.get_latest_initial_values()
        if init is not None and init.struct_id:
            res = init.struct_id.id
        return res

    @api.model
    def _default_get_trial_date_end(self):

        res = False
        init = self.get_latest_initial_values()
        if init is not None and init.trial_period and init.trial_period > 0:
            date_end = datetime.now().date() + timedelta(days=init.trial_period)
            res = date_end.strftime(OE_DFORMAT)
        return res

    wage = fields.Monetary(default=lambda self: self._default_get_wage())
    struct_id = fields.Many2one(default=lambda self: self._default_get_struct())
    trial_date_end = fields.Date(default=lambda self: self._default_get_trial_date_end())

    @api.onchange('job_id')
    def _onchange_job_id(self):

        if self.job_id.id:
            wage = self._default_get_wage(job_id=self.job_id.id)
            return {'value': {'wage': wage}}
        return False


    @api.model
    def get_latest_initial_values(self, today_str=None):
        """Return a record with an effective date before today_str
        but greater than all others
        """

        init_obj = self.env['hr.contract.init']

        if today_str is None:
            today_str = datetime.now().strftime(OE_DFORMAT)

        date_today = datetime.strptime(today_str, OE_DFORMAT).date()

        res = None
        initial_settings = init_obj.search([('date', '<=', today_str), ('state', '=', 'approve')])

        for init in initial_settings:
            d = datetime.strptime(init.date, OE_DFORMAT).date()
            if d <= date_today:
                if res is None:
                    res = init
                elif d > datetime.strptime(res.date, OE_DFORMAT).date():
                    res = init

        return res
