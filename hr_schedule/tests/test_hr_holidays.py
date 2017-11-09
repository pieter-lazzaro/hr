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

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pytz

from odoo.tests import common
from odoo import fields
from odoo.exceptions import UserError
from .common import HrScheduleTestCase


class test_hr_schedule(HrScheduleTestCase):

    def setUp(self):
        super(test_hr_schedule, self).setUp()

    def test_leave_removes_from_schedule(self):
        """ Test that leaves will be removed from the schedule """
        holidays_status_unlimited = self.env['hr.holidays.status'].create({
            'name': 'NotLimited',
            'limit': True,
        })
        leave1 = self.leave_model.create({
            'name': 'test leave',
            'date_from': self.start_of_week + relativedelta(days=1),
            'date_to': self.start_of_week + relativedelta(days=2),
            'holiday_status_id': holidays_status_unlimited.id,
            'employee_id': self.employee.id
        })

        schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'date_start': fields.Date.to_string(self.start_of_week),
            'date_end': fields.Date.to_string(self.end_of_week)
        })

        # Shift on the monday
        shift1 = self.detail_model.create({
            'schedule_id': schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '0',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 10, 0)),
        })

        shift2 = self.detail_model.create({
            'schedule_id': schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 2',
            'dayofweek': '1',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 0)),
        })

        leave1.action_validate()

        self.assertNotIn(shift2, schedule.detail_ids)

    def test_partial_and_end(self):
        """ Test that leaves that cover part of a shift will end the shift when the leave starts """
        holidays_status_unlimited = self.env['hr.holidays.status'].create({
            'name': 'NotLimited',
            'limit': True,
        })

        schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'date_start': fields.Date.to_string(self.start_of_week),
            'date_end': fields.Date.to_string(self.end_of_week)
        })

        shift = self.detail_model.create({
            'schedule_id': schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '0',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 10, 0)),
        })

        leave = self.leave_model.create({
            'name': 'test leave',
            'date_from': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 30)),
            'date_to': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 30)),
            'holiday_status_id': holidays_status_unlimited.id,
            'employee_id': self.employee.id
        })

        leave.action_validate()

        self.assertEqual(shift.date_end, fields.Datetime.to_string(
            self._datetime_utc(2017, 10, 30, 9, 30)))

    def test_partial_at_start(self):
        """ Test that leaves that cover part of a shift will end the shift when the leave starts """
        holidays_status_unlimited = self.env['hr.holidays.status'].create({
            'name': 'NotLimited',
            'limit': True,
        })

        schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'date_start': fields.Date.to_string(self.start_of_week),
            'date_end': fields.Date.to_string(self.end_of_week)
        })

        shift = self.detail_model.create({
            'schedule_id': schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '0',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 10, 0)),
        })

        leave = self.leave_model.create({
            'name': 'test leave',
            'date_from': fields.Datetime.to_string(self._datetime_utc(2017, 10, 29, 9, 30)),
            'date_to': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 30)),
            'holiday_status_id': holidays_status_unlimited.id,
            'employee_id': self.employee.id
        })

        leave.action_validate()

        self.assertEqual(shift.date_start, fields.Datetime.to_string(
            self._datetime_utc(2017, 10, 30, 9, 30)))
