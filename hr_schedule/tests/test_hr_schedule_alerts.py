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

from .common import HrScheduleTestCase


class test_hr_schedule_alerts(HrScheduleTestCase):

    def setUp(self):
        super(test_hr_schedule_alerts, self).setUp()
        self.attendance_model = self.env['hr.attendance']

        self.schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'date_start': fields.Date.today(),
            'date_end': fields.Date.to_string(date.today() + timedelta(weeks=1))
        })

    def test_unscheduled_attendance_alert(self):

        self.detail_model.create({
            'schedule_id': self.schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '1',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 0)),
        })

        attendance = self.attendance_model.create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 0)),
        })

        self.assertEqual(1, len(attendance.alert_ids))
        self.assertEqual(attendance.alert_ids.rule_id.code, 'UNSCHEDATT')

    def test_tardy_attendance_alert(self):

        self.detail_model.create({
            'schedule_id': self.schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '1',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 0)),
        })

        attendance = self.attendance_model.create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 15)),
        })

        self.assertEqual(1, len(attendance.alert_ids))
        self.assertEqual(attendance.alert_ids.rule_id.code, 'TARDY')

    def test_tardy_within_grace_period_attendance_alert(self):
    
        self.detail_model.create({
            'schedule_id': self.schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '1',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 0)),
        })

        attendance = self.attendance_model.create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 5)),
        })

        self.assertEqual(0, len(attendance.alert_ids))

    def test_leave_late_alert(self):
    
        self.detail_model.create({
            'schedule_id': self.schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '1',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 0)),
        })

        attendance = self.attendance_model.create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'check_out': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 11, 0)),
        })

        self.assertEqual(1, len(attendance.alert_ids))
        self.assertEqual(attendance.alert_ids.rule_id.code, 'OUTLATE')

    def test_leave_late_within_grace_period(self):
        
        self.detail_model.create({
            'schedule_id': self.schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '1',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 0)),
        })

        attendance = self.attendance_model.create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'check_out': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 5)),
        })

        self.assertEqual(0, len(attendance.alert_ids))

    def test_leave_early_alert(self):
        
        self.detail_model.create({
            'schedule_id': self.schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '1',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 0)),
        })

        attendance = self.attendance_model.create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'check_out': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 30)),
        })

        self.assertEqual(1, len(attendance.alert_ids))
        self.assertEqual(attendance.alert_ids.rule_id.code, 'OUTEARLY')

    def test_leave_early_within_grace_period(self):
        
        self.detail_model.create({
            'schedule_id': self.schedule.id,
            'employee_id': self.employee.id,
            'name': 'shift 1',
            'dayofweek': '1',
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 10, 0)),
        })

        attendance = self.attendance_model.create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 0)),
            'check_out': fields.Datetime.to_string(self._datetime_utc(2017, 10, 31, 9, 55)),
        })

        self.assertEqual(0, len(attendance.alert_ids))
