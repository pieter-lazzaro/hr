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
from odoo.tools.translate import _
from odoo.exceptions import UserError

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
    )
    worktime_ids = fields.One2many(
        'hr.schedule.template.worktime',
        'template_id',
        'Working Time',
    )
    restday_ids = fields.Many2many(
        'hr.schedule.weekday',
        'schedule_template_restdays_rel',
        'sched_id',
        'weekday_id',
        string='Rest Days',
    )

    _defaults = {
        'company_id': (
            lambda self, cr, uid, context:
            self.pool.get('res.company')._company_default_get(
                cr, uid, 'resource.calendar', context=context
            )
        ),
    }

    def get_rest_days(self, cr, uid, t_id, context=None):
        """If the rest day(s) have been explicitly specified that's
        what is returned, otherwise a guess is returned based on the
        week days that are not scheduled. If an explicit rest day(s)
        has not been specified an empty list is returned. If it is able
        to figure out the rest days it will return a list of week day
        integers with Monday being 0.
        """

        tpl = self.browse(cr, uid, t_id, context=context)
        if tpl.restday_ids:
            res = [rd.sequence for rd in tpl.restday_ids]
        else:
            weekdays = ['0', '1', '2', '3', '4', '5', '6']
            scheddays = []
            scheddays = [
                wt.dayofweek
                for wt in tpl.worktime_ids
                if wt.dayofweek not in scheddays
            ]
            res = [int(d) for d in weekdays if d not in scheddays]
            # If there are no work days return nothing instead of *ALL* the
            # days in the week
            if len(res) == 7:
                res = []

        return res

    def get_hours_by_weekday(self, cr, uid, tpl_id, day_no, context=None):
        """Return the number working hours in the template for day_no.
        For day_no 0 is Monday.
        """

        delta = timedelta(seconds=0)
        tpl = self.browse(cr, uid, tpl_id, context=context)
        for worktime in tpl.worktime_ids:
            if int(worktime.dayofweek) != day_no:
                continue

            fromHour, fromSep, fromMin = worktime.hour_from.partition(':')
            toHour, toSep, toMin = worktime.hour_to.partition(':')
            if len(fromSep) == 0 or len(toSep) == 0:
                raise UserError(_('Invalid Data' 'Format of working hours is incorrect'))

            delta += (
                datetime.strptime(toHour + ':' + toMin, '%H:%M') -
                datetime.strptime(fromHour + ':' + fromMin, '%H:%M')
            )

        return float(delta.seconds / 60) / 60.0
