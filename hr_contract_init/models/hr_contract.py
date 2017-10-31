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

import logging
from datetime import datetime, timedelta

from odoo.addons import decimal_precision as dp
from odoo import fields, models, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from odoo.tools.translate import _
from odoo.exceptions import UserError


class HrContract(models.Model):
    
    _inherit = 'hr.contract'

    def _default_get_wage(self, job_id=None):
        ''' Returns the wage for job with id job_id. '''
        res = 0
        default = 0
        init = self.get_latest_initial_values()

        if job_id:
            job = self.env['hr.job'].browse(job_id)
        else:
            job = False

        if init is not None:
            for line in init.wage_ids:
                if job_id is not None and line.job_id.id == job_id:
                    res = line.starting_wage
                elif job:
                    cat_id = False
                    category_ids = [c.id for c in line.category_ids]
                    for ci in job.category_ids:
                        if ci.id in category_ids:
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

    def _default_get_struct(self):

        res = False
        init = self.get_latest_initial_values()
        if init is not None and init.struct_id:
            res = init.struct_id.id
        return res

    def _default_get_trial_date_end(self):
        _logger.info(self.read())
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
            today_str = fields.Date.today()

        date_today = fields.Date.from_string(today_str)

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
