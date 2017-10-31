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

from odoo import models, fields

class hr_schedule_request(models.Model):

    _name = 'hr.schedule.request'
    _description = 'Change Request'

    _inherit = ['mail.thread']

    employee_id = fields.Many2one(
        'hr.employee',
        'Employee',
        required=True,
    )
    date = fields.Date(
        'Date',
        required=True,
    )
    type = fields.Selection(
        [
            ('missedp', 'Missed Punch'),
            ('adjp', 'Punch Adjustment'),
            ('absence', 'Absence'),
            ('schedadj', 'Schedule Adjustment'),
            ('other', 'Other'),
        ],
        'Type',
        required=True,
    )
    message = fields.Text(
        'Message',
    )
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('auth', 'Authorized'),
            ('denied', 'Denied'),
            ('cancel', 'Cancelled'),
        ],
        'State',
        required=True,
        readonly=True,
    )

    _defaults = {
        'state': 'pending',
    }
