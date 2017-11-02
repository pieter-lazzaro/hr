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


class test_hr_schedule_working_times(common.TransactionCase):
    
    def setUp(self):
        super(test_hr_schedule_working_times, self).setUp()

        self.schedule_model = self.env['hr.schedule']
        self.template_model = self.env['hr.schedule.template']
        self.detail_model = self.env['hr.schedule.detail']
        self.worktime_model = self.env['hr.schedule.template.worktime']
        self.contract_model = self.env['hr.contract']

        self.employee = self.env['hr.employee'].create({'name': 'test employee'})
        self.contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
        })
        self.shifts = 0


    def _datetime(self, year, month, day, hour=0, minute=0, tzinfo=None):
        if tzinfo is None:
            tzinfo = pytz.timezone(self.env.user.tz)
        
        d = datetime(year, month, day, hour, minute)
        return tzinfo.localize(d)

    def _convert_to_utc(self, timestamp):
        return pytz.utc.localize(fields.Datetime.from_string(timestamp))

    def _convert_to_user_tz(self, timestamp):
        datetime_utc = self._convert_to_utc(timestamp)
        user_tz = pytz.timezone(self.env.user.tz)
        datetime_user_tz = datetime_utc.astimezone(user_tz)
        return datetime_user_tz

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

    def test_date_calculations(self):
        """ Test worktimes date calculations """
        start_of_week = datetime(2017, 10, 30)

        template = self.template_model.create({
            'name': 'test template'
        })

        shift = self._create_shift(template, 1, '0', 9.0, 12.5)
        
        shift.start_of_week = start_of_week
        
        self.assertEqual(shift.date_start, '2017-10-30 09:00:00')
        self.assertEqual(shift.date_end, '2017-10-30 12:30:00')

        shift.date_start = '2017-10-30 10:00:00'
        shift.date_end = '2017-10-30 13:30:00'

        shift._set_date_start()
        shift._set_date_end()
        
        self.assertEqual(shift.hour_from, 10.0)
        self.assertEqual(shift.hour_to, 13.5)
