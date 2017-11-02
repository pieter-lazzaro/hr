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

from odoo import fields, models, api


class hr_schedule_generate(models.TransientModel):

    _name = 'hr.schedule.generate'
    _description = 'Generate Schedules'

    date_start = fields.Date(
        'Start',
        required=True,
    )
    no_weeks = fields.Integer(
        'Number of weeks',
        required=True,
        default=2
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'hr_employee_schedule_rel',
        'generate_id',
        'employee_id',
        'Employees',
    )

    @api.onchange('date_start')
    def onchange_start_date(self):

        if self.date_start:
            dStart = datetime.strptime(self.date_start, '%Y-%m-%d').date()
            # The schedule must start on a Monday
            if dStart.weekday() == 0:
                self.date_start = dStart.strftime('%Y-%m-%d')

    def generate_schedules(self):

        sched_obj = self.env['hr.schedule']
        ee_obj = self.env['hr.employee']

        dStart = fields.Date.from_string(self.date_start)
        dEnd = dStart + relativedelta(weeks=+self.no_weeks, days=-1)

        sched_ids = []
        if len(self.employee_ids) > 0:
            for ee in self.employee_ids:
                if not ee.contract_id or not ee.contract_id.schedule_template_id:
                    continue

                # If there are overlapping schedules, don't create
                #
                overlap_sched_ids = sched_obj.search([('employee_id', '=', ee.id),
                                                      ('date_start', '<=', dEnd.strftime(
                                                          '%Y-%m-%d')),
                                                      ('date_end', '>=', dStart.strftime('%Y-%m-%d'))])
                if len(overlap_sched_ids) > 0:
                    continue

                sched = {
                    'name': ee.name + ': ' + self.date_start + ' Wk ' + str(dStart.isocalendar()[1]),
                    'employee_id': ee.id,
                    'template_id': ee.contract_id.schedule_template_id.id,
                    'date_start': dStart.strftime('%Y-%m-%d'),
                    'date_end': dEnd.strftime('%Y-%m-%d'),
                }

                sched_ids.append(sched_obj.create(sched).id)

        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.schedule',
            'domain': [('id', 'in', sched_ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': True,
            'context': self.env.context,
        }
