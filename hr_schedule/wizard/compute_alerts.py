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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models


class compute_alerts(models.TransientModel):

    _name = 'hr.schedule.alert.compute'
    _description = 'Check Alerts'

    date_start = fields.Date(
        'Start',
        required=True,
    )
    date_end = fields.Date(
        'End',
        required=True,
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'hr_employee_alert_rel',
        'generate_id',
        'employee_id',
        'Employees',
    )

    def generate_alerts(self):

        alert_obj = self.env['hr.schedule.alert']

        date_start = fields.Datetime.from_string(self.date_start)
        date_end = fields.Datetime.from_string(self.date_end)

        for employee_id in self.employee_ids:
            alert_obj.compute_alerts_by_employee(employee_id, date_start, date_end)

        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.schedule.alert',
            'domain': [
                ('employee_id', 'in', self.employee_ids.ids),
                '&',
                ('name', '>=', self.date_start + ' 00:00:00'),
                ('name', '<=', self.date_end + ' 23:59:59')
            ],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': True,
            'context': self.env.context,
        }
