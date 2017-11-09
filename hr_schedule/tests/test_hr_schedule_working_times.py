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


class test_hr_schedule_working_times(HrScheduleTestCase):

    def setUp(self):
        super(test_hr_schedule_working_times, self).setUp()

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
    
    def test_start_of_week_calculations(self):
        """ Test start of week calculations """

        test_cases = [
            (self._datetime_utc(2017, 10, 30), self._datetime_utc(2017, 10, 30)),
            (self._datetime_utc(2017, 11, 1), self._datetime_utc(2017, 10, 30)),
            (self._datetime_utc(2017, 11, 2), self._datetime_utc(2017, 10, 30)),
            (self._datetime_utc(2017, 11, 3), self._datetime_utc(2017, 10, 30)),
            (self._datetime_utc(2017, 11, 4), self._datetime_utc(2017, 10, 30)),
            (self._datetime_utc(2017, 11, 5), self._datetime_utc(2017, 11, 6)), ## This case handles DST
        ]

        for today, expected in test_cases:
            start_of_week = self.worktime_model.get_start_of_week(today)
            self.assertEqual(expected, start_of_week, msg='%s: %s vs %s' % (today.isoformat(), expected.isoformat(), start_of_week))


    def test_basic_date_calculations(self):
        """ Test basic worktimes date calculations """

        template = self.template_model.create({
            'name': 'test template'
        })

        shift = self._create_shift(template, 1, '0', 9.0, 12.5)
        shift.start_of_week = self.start_of_week

        date_start = fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 9, 0))
        date_end = fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 12, 30))

        self.assertEqual(shift.date_start, date_start)
        self.assertEqual(shift.date_end, date_end)

        shift.date_start = fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 10, 0))
        shift.date_end = fields.Datetime.to_string(self._datetime_utc(2017, 10, 30, 13, 30))

        shift._set_dates()

        self.assertEqual(shift.hour_from, 10.0)
        self.assertEqual(shift.hour_to, 13.5)

    def test_multiple_week_date_calculations(self):
        """ Test multiple week worktimes date calculations """
        
        template = self.template_model.create({
            'name': 'test template'
        })

        shift = self._create_shift(template, 2, '0', 9.0, 12.5)
        shift.start_of_week = self.start_of_week

        date_start = fields.Datetime.to_string(self._datetime_utc(2017, 11, 6, 9, 0))
        date_end = fields.Datetime.to_string(self._datetime_utc(2017, 11, 6, 12, 30))

        self.assertEqual(shift.date_start, date_start)
        self.assertEqual(shift.date_end, date_end)

        shift.date_start = fields.Datetime.to_string(self._datetime_utc(2017, 11, 6, 10, 0))
        shift.date_end = fields.Datetime.to_string(self._datetime_utc(2017, 11, 6, 13, 30))

        shift._set_dates()

        self.assertEqual(shift.hour_from, 10.0)
        self.assertEqual(shift.hour_to, 13.5)
        self.assertEqual(shift.dayofweek, '0')
        self.assertEqual(shift.week, 2)

    def test_quick_create(self):
        """ Test create will work with the data passed from a quick add """

        template = self.template_model.create({
            'name': 'test template'
        })

        shift = self.worktime_model.with_context(
            active_id=template.id,
            active_model="hr.schedule.template"
        ).create({
            'name': 'test shift',
            'start_of_week': fields.Datetime.to_string(self._datetime_utc(2017, 10, 30)),
            'date_start': fields.Datetime.to_string(self._datetime_utc(2017, 11, 6, 9, 0)),
            'date_end': fields.Datetime.to_string(self._datetime_utc(2017, 11, 6, 12, 30)),
        })

        self.assertEqual(shift.template_id.id, template.id)
        self.assertEqual(shift.hour_from, 9.0)
        self.assertEqual(shift.hour_to, 12.5)
        self.assertEqual(shift.week, 2)

    def test_defalt_get(self):
        """ Test default get """

        expected = {
            'hour_from': 9.0,
            'hour_to': 12.5,
            'week': 2,
        }

        defaults = self.worktime_model.with_context(
            default_start_of_week=fields.Datetime.to_string(self._datetime_utc(2017, 10, 30)),
            default_date_start=fields.Datetime.to_string(self._datetime_utc(2017, 11, 6, 9, 0)),
            default_date_end=fields.Datetime.to_string(self._datetime_utc(2017, 11, 6, 12, 30)),
        ).default_get(['hour_from', 'hour_to', 'week', 'name'])

        self.assertEqual(expected, defaults)


    def test_defalt_get_without_dates(self):
        """ Test default get """

        expected = {
            'hour_from': 0,
            'hour_to': 0,
            'week': 1,
        }

        defaults = self.worktime_model.default_get(['hour_from', 'hour_to', 'week', 'name'])

        self.assertEqual(expected, defaults)
