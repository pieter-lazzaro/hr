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

