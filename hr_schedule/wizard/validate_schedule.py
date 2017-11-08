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

from odoo import netsvc

from odoo import fields, models

import logging
_logger = logging.getLogger(__name__)


class department_selection(models.TransientModel):

    _name = 'hr.schedule.validate.departments'
    _description = 'Department Selection for Validation'


    department_ids = fields.Many2many(
        'hr.department',
        'hr_department_group_rel',
        'employee_id',
        'department_id',
        'Departments',
    )

    def view_schedules(self):
        self.ensure_one()
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.schedule',
            'domain': [
                ('department_id', 'in', self.department_ids.ids),
                ('state', 'in', ['draft']),
            ],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': self.env.context,
        }

    def do_validate(self):
        self.ensure_one()

        sched_ids = self.env['hr.schedule'].search([
                ('department_id', 'in', self.department_ids.ids)
            ])
        for sched_id in sched_ids:
            sched_id.signal_validate()

        return {'type': 'ir.actions.act_window_close'}
