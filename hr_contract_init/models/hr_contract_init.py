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

from odoo.addons import decimal_precision as dp
from odoo import fields, models, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from odoo.tools.translate import _
from odoo.exceptions import UserError

class contract_init(models.Model):

    _name = 'hr.contract.init'
    _description = 'Initial Contract Settings'

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

