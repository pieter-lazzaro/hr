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

        self.shifts = 0
    
    def _create_shift(self, template, week, day, hour_from, hour_to):
        self.shifts += 1
        return self.worktime_model.create({
            'name': 'shift %d' % self.shifts,
            'week': week,
            'dayofweek': day,
            'hour_from': hour_from,
            'hour_to': hour_to,
            'template_id': template.id
        })

    def test_generate_basic_schedule(self):
        """ Test a basic schedule template can generate a schedule """
        start_of_week = datetime(2017, 10, 30)
        end_of_week = start_of_week + relativedelta(weeks=1) - relativedelta(days=1)

        template = self.template_model.create({
            'name': 'test template'
        })

        self.contract.schedule_template_id = template.id
        self.contract.date_start = start_of_week

        self._create_shift(template, 1, '0', 9.0, 12.5)
        self._create_shift(template, 1, '0', 13.0, 17.0)
        self._create_shift(template, 1, '1', 9.0, 12.5)
        self._create_shift(template, 1, '1', 13.0, 17.0)
        self._create_shift(template, 1, '2', 9.0, 12.5)
        self._create_shift(template, 1, '2', 13.0, 17.0)
        self._create_shift(template, 1, '3', 9.0, 12.5)
        self._create_shift(template, 1, '3', 13.0, 17.0)
        self._create_shift(template, 1, '4', 9.0, 12.5)
        self._create_shift(template, 1, '4', 13.0, 17.0)

        schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'template_id': template.id,
            'date_start': fields.Date.to_string(start_of_week),
            'date_end': fields.Date.to_string(end_of_week)
        })
        expected_shifts = [
            (self._datetime_utc(2017, 10, 30, 9), self._datetime_utc(2017, 10, 30, 12, 30)),
            (self._datetime_utc(2017, 10, 30, 13), self._datetime_utc(2017, 10, 30, 17, 0)),
            (self._datetime_utc(2017, 10, 31, 9), self._datetime_utc(2017, 10, 31, 12, 30)),
            (self._datetime_utc(2017, 10, 31, 13), self._datetime_utc(2017, 10, 31, 17, 0)),
            (self._datetime_utc(2017, 11, 1, 9), self._datetime_utc(2017, 11, 1, 12, 30)),
            (self._datetime_utc(2017, 11, 1, 13), self._datetime_utc(2017, 11, 1, 17, 0)),
            (self._datetime_utc(2017, 11, 2, 9), self._datetime_utc(2017, 11, 2, 12, 30)),
            (self._datetime_utc(2017, 11, 2, 13), self._datetime_utc(2017, 11, 2, 17, 0)),
            (self._datetime_utc(2017, 11, 3, 9), self._datetime_utc(2017, 11, 3, 12, 30)),
            (self._datetime_utc(2017, 11, 3, 13), self._datetime_utc(2017, 11, 3, 17, 0)),
        ]

        for i, shift in enumerate(schedule.detail_ids):
            self.assertEqual(shift.date_start, fields.Datetime.to_string(expected_shifts[i][0]))
            self.assertEqual(shift.date_end, fields.Datetime.to_string(expected_shifts[i][1]))

    def test_generate_multiple_week_schedule(self):
        """ Test a multiple week schedule template can generate a schedule """
        start_of_week = datetime(2017, 10, 30)
        end_of_week = start_of_week + relativedelta(weeks=2) - relativedelta(days=1)

        template = self.template_model.create({
            'name': 'test template'
        })

        self.contract.schedule_template_id = template.id
        self.contract.date_start = start_of_week

        self._create_shift(template, 1, '0', 9.0, 12.5)
        self._create_shift(template, 1, '0', 13.0, 17.0)
        self._create_shift(template, 1, '2', 9.0, 12.5)
        self._create_shift(template, 1, '2', 13.0, 17.0)
        self._create_shift(template, 1, '4', 9.0, 12.5)
        self._create_shift(template, 1, '4', 13.0, 17.0)
        self._create_shift(template, 2, '1', 9.0, 12.5)
        self._create_shift(template, 2, '1', 13.0, 17.0)
        self._create_shift(template, 2, '3', 9.0, 12.5)
        self._create_shift(template, 2, '3', 13.0, 17.0)

        schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'template_id': template.id,
            'date_start': fields.Date.to_string(start_of_week),
            'date_end': fields.Date.to_string(end_of_week)
        })

        expected_shifts = [
            (self._datetime_utc(2017, 10, 30, 9), self._datetime_utc(2017, 10, 30, 12, 30)),
            (self._datetime_utc(2017, 10, 30, 13), self._datetime_utc(2017, 10, 30, 17, 0)),
            (self._datetime_utc(2017, 11, 1, 9), self._datetime_utc(2017, 11, 1, 12, 30)),
            (self._datetime_utc(2017, 11, 1, 13), self._datetime_utc(2017, 11, 1, 17, 0)),
            (self._datetime_utc(2017, 11, 3, 9), self._datetime_utc(2017, 11, 3, 12, 30)),
            (self._datetime_utc(2017, 11, 3, 13), self._datetime_utc(2017, 11, 3, 17, 0)),
            (self._datetime_utc(2017, 11, 7, 9), self._datetime_utc(2017, 11, 7, 12, 30)),
            (self._datetime_utc(2017, 11, 7, 13), self._datetime_utc(2017, 11, 7, 17, 0)),
            (self._datetime_utc(2017, 11, 9, 9), self._datetime_utc(2017, 11, 9, 12, 30)),
            (self._datetime_utc(2017, 11, 9, 13), self._datetime_utc(2017, 11, 9, 17, 0)),
        ]

        for i, shift in enumerate(schedule.detail_ids):
            self.assertEqual(shift.date_start, fields.Datetime.to_string(expected_shifts[i][0]))
            self.assertEqual(shift.date_end, fields.Datetime.to_string(expected_shifts[i][1]))

    def test_generate_partial_multiple_week_schedule(self):
        """ Test a only half a multiple week schedule template """
        start_of_week = datetime(2017, 10, 30)
        end_of_week = start_of_week + relativedelta(weeks=1) - relativedelta(days=1)

        template = self.template_model.create({
            'name': 'test template'
        })

        self.contract.schedule_template_id = template.id
        self.contract.date_start = start_of_week

        self._create_shift(template, 1, '0', 9.0, 12.5)
        self._create_shift(template, 1, '0', 13.0, 17.0)
        self._create_shift(template, 1, '2', 9.0, 12.5)
        self._create_shift(template, 1, '2', 13.0, 17.0)
        self._create_shift(template, 1, '4', 9.0, 12.5)
        self._create_shift(template, 1, '4', 13.0, 17.0)
        self._create_shift(template, 2, '1', 9.0, 12.5)
        self._create_shift(template, 2, '1', 13.0, 17.0)
        self._create_shift(template, 2, '3', 9.0, 12.5)
        self._create_shift(template, 2, '3', 13.0, 17.0)

        schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'template_id': template.id,
            'date_start': fields.Date.to_string(start_of_week),
            'date_end': fields.Date.to_string(end_of_week)
        })

        expected_shifts = [
            (self._datetime_utc(2017, 10, 30, 9), self._datetime_utc(2017, 10, 30, 12, 30)),
            (self._datetime_utc(2017, 10, 30, 13), self._datetime_utc(2017, 10, 30, 17, 0)),
            (self._datetime_utc(2017, 11, 1, 9), self._datetime_utc(2017, 11, 1, 12, 30)),
            (self._datetime_utc(2017, 11, 1, 13), self._datetime_utc(2017, 11, 1, 17, 0)),
            (self._datetime_utc(2017, 11, 3, 9), self._datetime_utc(2017, 11, 3, 12, 30)),
            (self._datetime_utc(2017, 11, 3, 13), self._datetime_utc(2017, 11, 3, 17, 0)),
        ]

        for i, shift in enumerate(schedule.detail_ids):
            self.assertEqual(shift.date_start, fields.Datetime.to_string(expected_shifts[i][0]))
            self.assertEqual(shift.date_end, fields.Datetime.to_string(expected_shifts[i][1]))

    def test_generate_overnight_schedule(self):
        """ Test a only half a multiple week schedule template """
        start_of_week = datetime(2017, 10, 30)
        end_of_week = start_of_week + relativedelta(weeks=1) - relativedelta(days=1)

        template = self.template_model.create({
            'name': 'test template'
        })

        self.contract.schedule_template_id = template.id
        self.contract.date_start = start_of_week

        self._create_shift(template, 1, '0', 22.0, 1.5)
        self._create_shift(template, 1, '1', 2.0, 5.0)
        self._create_shift(template, 1, '1', 22.0, 1.5)
        self._create_shift(template, 1, '2', 2.0, 5.0)
        self._create_shift(template, 1, '2', 22.0, 1.5)
        self._create_shift(template, 1, '3', 2.0, 5.0)

        schedule = self.schedule_model.create({
            'name': 'test schedule',
            'employee_id': self.employee.id,
            'template_id': template.id,
            'date_start': fields.Date.to_string(start_of_week),
            'date_end': fields.Date.to_string(end_of_week)
        })

        expected_shifts = [
            (self._datetime_utc(2017, 10, 30, 22, 0), self._datetime_utc(2017, 10, 31, 1, 30)),
            (self._datetime_utc(2017, 10, 31, 2, 0), self._datetime_utc(2017, 10, 31, 5, 0)),
            (self._datetime_utc(2017, 10, 31, 22, 0), self._datetime_utc(2017, 11, 1, 1, 30)),
            (self._datetime_utc(2017, 11, 1, 2, 0), self._datetime_utc(2017, 11, 1, 5, 0)),
            (self._datetime_utc(2017, 11, 1, 22, 0), self._datetime_utc(2017, 11, 2, 1, 30)),
            (self._datetime_utc(2017, 11, 2, 2, 0), self._datetime_utc(2017, 11, 2, 5, 0)),
        ]

        for i, shift in enumerate(schedule.detail_ids):
            self.assertEqual(shift.date_start, fields.Datetime.to_string(expected_shifts[i][0]), msg=i)
            self.assertEqual(shift.date_end, fields.Datetime.to_string(expected_shifts[i][1]), msg=i)