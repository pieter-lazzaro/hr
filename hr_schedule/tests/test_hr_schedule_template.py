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

from datetime import date

from odoo.tests import common
from odoo import fields
from odoo.exceptions import UserError


class test_hr_schedule_template(common.TransactionCase):
    def setUp(self):
        super(test_hr_schedule_template, self).setUp()
        self.template_model = self.env['hr.schedule.template']
        self.worktime_model = self.env['hr.schedule.template.worktime']
        self.weekday_model = self.env['hr.schedule.weekday']

    def test_get_rest_days_when_defined(self):
        """
        Test that templates compute the right rest days when explicitly defined
        """

        restdays_ids = self.weekday_model.search(
            [('sequence', 'in', ['5', '6'])]).mapped(lambda r: r.id)

        template = self.template_model.create({
            'name': 'test template',
            'restday_ids': [(6, '', restdays_ids)]
        })

        restdays = template.get_rest_days()

        self.assertEqual([5, 6], restdays)

    def test_get_rest_days_when_not_defined(self):
        """
        Test that templates compute the right rest days when not explicitly defined
        """

        template = self.template_model.create({
            'name': 'test template',
        })

        self.worktime_model.create({
            'name': 'shift1',
            'dayofweek': '0',
            'hour_from': 9.0,
            'hour_to': 13.0,
            'template_id': template.id
        })
        restdays = template.get_rest_days()

        self.assertEqual([1, 2, 3, 4, 5, 6], restdays)

    def test_get_worktime_for_day_with_single_shift(self):
        """
        Test that templates compute the right number of hours worked when there is a single shift
        """

        template = self.template_model.create({
            'name': 'test template',
        })

        self.worktime_model.create({
            'name': 'shift1',
            'dayofweek': '0',
            'hour_from': 9.0,
            'hour_to': 13.0,
            'template_id': template.id
        })

        worked_hours = template.get_hours_by_weekday(0)

        self.assertEqual(4, worked_hours)

    def test_get_worktime_for_day_with_multiple_shifts(self):
        """
        Test that templates compute the right number of hours worked there is multiple shifts
        """

        template = self.template_model.create({
            'name': 'test template',
        })

        self.worktime_model.create({
            'name': 'shift1',
            'dayofweek': '0',
            'hour_from': 9.0,
            'hour_to': 13.0,
            'template_id': template.id
        })

        self.worktime_model.create({
            'name': 'shift2',
            'dayofweek': '0',
            'hour_from': 15.0,
            'hour_to': 18.5,
            'template_id': template.id
        })

        worked_hours = template.get_hours_by_weekday(0)

        self.assertEqual(7.5, worked_hours)

    def test_get_worktime_for_day_with_overnight_shift(self):
        """
        Test that templates compute the right number of hours worked there is multiple shifts
        """

        template = self.template_model.create({
            'name': 'test template',
        })

        self.worktime_model.create({
            'name': 'shift1',
            'dayofweek': '0',
            'hour_from': 22.0,
            'hour_to': 3.0,
            'template_id': template.id
        })

        worked_hours = template.get_hours_by_weekday(0)

        self.assertEqual(5, worked_hours)
