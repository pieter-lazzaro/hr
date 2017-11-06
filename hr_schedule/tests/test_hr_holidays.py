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


class test_hr_schedule(common.TransactionCase):

    def setUp(self):
        super(test_hr_schedule, self).setUp()

        self.schedule_model = self.env['hr.schedule']
        self.template_model = self.env['hr.schedule.template']
        self.detail_model = self.env['hr.schedule.detail']
        self.worktime_model = self.env['hr.schedule.template.worktime']
        self.contract_model = self.env['hr.contract']
        self.leave_model = self.env['hr.holidays']

        self.employee = self.env['hr.employee'].create(
            {'name': 'test employee'})
        self.contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
        })
        self.shifts = 0

        self.start_of_week = self._datetime_utc(2017, 10, 30)
        self.end_of_week = self.start_of_week + \
            relativedelta(weeks=1) - relativedelta(days=1)

    def _datetime(self, year, month, day, hour=0, minute=0, tzinfo=None):
        if tzinfo is None:
            tzinfo = pytz.timezone(self.env.user.tz)

        d = datetime(year, month, day, hour, minute)
        return tzinfo.localize(d)

    def _datetime_utc(self, year, month, day, hour=0, minute=0, tzinfo=None):
        d = self._datetime(year, month, day, hour, minute, tzinfo)
        return d.astimezone(pytz.utc)

    def _convert_to_utc(self, timestamp):
        return pytz.utc.localize(fields.Datetime.from_string(timestamp))

    def _convert_to_user_tz(self, timestamp):
        datetime_utc = self._convert_to_utc(timestamp)
        user_tz = pytz.timezone(self.env.user.tz)
        datetime_user_tz = datetime_utc.astimezone(user_tz)
        return datetime_user_tz

    def test_leave_removes_from_schedule(self):
        """ Test that leaves will be removed from the schedule """
        self.holidays_status_unlimited = self.env['hr.holidays.status'].create({
            'name': 'NotLimited',
            'limit': True,
        })
        leave1 = self.leave_model.create({
            'name': 'test leave',
            'date_from': self.start_of_week + relativedelta(days=1),
            'date_to': self.start_of_week + relativedelta(days=2),
            'holiday_status_id': self.holidays_status_unlimited.id,
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
        self.holidays_status_unlimited = self.env['hr.holidays.status'].create({
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
            'holiday_status_id': self.holidays_status_unlimited.id,
            'employee_id': self.employee.id
        })

        leave.action_validate()

        self.assertEqual(shift.date_end, fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 30)))

    def test_partial_at_start(self):
        """ Test that leaves that cover part of a shift will end the shift when the leave starts """
        self.holidays_status_unlimited = self.env['hr.holidays.status'].create({
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
            'holiday_status_id': self.holidays_status_unlimited.id,
            'employee_id': self.employee.id
        })

        leave.action_validate()

        self.assertEqual(shift.date_start, fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 30)))