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
from datetime import datetime, timedelta

from odoo import models, fields


class hr_schedule_template(models.Model):

    _name = 'hr.schedule.template'
    _description = 'Employee Working Schedule Template'

    name = fields.Char(
        "Name",
        size=64,
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=False,
        default=lambda self: self.env.user.company_id.id
    )
    worktime_ids = fields.One2many(
        'hr.schedule.template.worktime',
        'template_id',
        'Working Time',
    )
    restday_ids = fields.Many2many(
        'hr.schedule.weekday',
        string='Rest Days',
    )

    def get_rest_days(self):
        """If the rest day(s) have been explicitly specified that's
        what is returned, otherwise a guess is returned based on the
        week days that are not scheduled. If an explicit rest day(s)
        has not been specified an empty list is returned. If it is able
        to figure out the rest days it will return a list of week day
        integers with Monday being 0.
        """

        self.ensure_one()

        if self.restday_ids:
            res = self.restday_ids.mapped(lambda r: r.sequence)
        else:
            weekdays = ['0', '1', '2', '3', '4', '5', '6']
            scheddays = []
            scheddays = [
                wt.dayofweek
                for wt in self.worktime_ids
                if wt.dayofweek not in scheddays
            ]
            res = [int(d) for d in weekdays if d not in scheddays]
            # If there are no work days return nothing instead of *ALL* the
            # days in the week
            if len(res) == 7:
                res = []

        return res

    def get_hours_by_weekday(self, day_no):
        """
        Return the number working hours in the template for day_no.
        For day_no 0 is Monday. All shifts starting on day_no will 
        be included.
        """
        self.ensure_one()

        delta = 0
        for worktime in self.worktime_ids:
            if int(worktime.dayofweek) != day_no:
                continue
            hours = (worktime.hour_to - worktime.hour_from)

            if hours < 0:
                hours = hours + 24
            delta = delta + hours

        return delta
