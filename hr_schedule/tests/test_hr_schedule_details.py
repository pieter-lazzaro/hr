##############################################################################
#
#    Copyright (C) 2017 Pieter Lazzaro. All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by
#    the Free Software Foundation, either version 3 of the License, or
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
##############################################################################

from datetime import date, datetime, timedelta

from odoo.tests import common
from odoo import fields
from odoo.exceptions import UserError


class test_hr_schedule_details(common.TransactionCase):
    def setUp(self):
        super(test_hr_schedule_details, self).setUp()
        self.schedule_model = self.env['hr.schedule']
        self.detail_model = self.env['hr.schedule.detail']

        self.employee = self.env['hr.employee'].create(
            {'name': 'test employee'})
        self.schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'date_start': fields.Date.today(),
            'date_end': fields.Date.to_string(date.today() + timedelta(weeks=1))
        })
        self.today = date.today()
        self.day_start = datetime(self.today.year, self.today.month, self.today.day)

    def test_hr_schedule_detail_begin_end(self):
        today = date.today()
        day_start = datetime(today.year, today.month, today.day)

        shifts = [
            (day_start + timedelta(hours=9), day_start + timedelta(hours=13)),
            (day_start + timedelta(hours=13.5), day_start + timedelta(hours=17)),
        ]

        detail = self.detail_model.create({
            'schedule_id': self.schedule.id,
            'name': 'test detail',
            'dayofweek': '0',
            'date_start': fields.Datetime.to_string(shifts[0][0]),
            'date_end': fields.Datetime.to_string(shifts[0][1]),
        })

        detail2 = self.detail_model.create({
            'schedule_id': self.schedule.id,
            'name': 'test detail 2',
            'dayofweek': '0',
            'date_start': fields.Datetime.to_string(shifts[1][0]),
            'date_end': fields.Datetime.to_string(shifts[1][1]),
        })

        times = self.detail_model.scheduled_begin_end_times(
            self.employee.id, date.today())
        self.assertEqual(shifts, times)

    def test_hr_schedule_scheduled_hours_for_day(self):

        shifts = {
            fields.Date.to_string(self.today): [
                (self.day_start + timedelta(hours=9),
                 self.day_start + timedelta(hours=13)),
                (self.day_start + timedelta(hours=13.5),
                 self.day_start + timedelta(hours=17)),
            ]
        }

        hours = self.detail_model.scheduled_hours_on_day_from_range(
            self.today, shifts)
        self.assertEqual(7.5, hours)
