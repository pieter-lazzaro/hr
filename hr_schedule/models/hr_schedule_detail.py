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

import time
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError

from .week_days import DAYOFWEEK_SELECTION


class schedule_detail(models.Model):
    _name = "hr.schedule.detail"
    _description = "Schedule Detail"

    @api.multi
    @api.depends('date_start')
    def _day_compute(self):
        for obj in self:
            day = self._get_day(obj.date_start)
            obj.day = fields.Date.to_string(day)

    def _get_day(self, date_and_time):

        if isinstance(date_and_time, str):
            date_and_time = fields.Datetime.from_string(date_and_time)

        datetime_as_utc = utc.localize(date_and_time)
        user_tz = timezone(self.env.user.tz)

        return datetime_as_utc.astimezone(user_tz).date()

    @api.depends('schedule_id')
    def _compute_employee_id(self):
        for record in self:
            record.employee_id = record.schedule_id.employee_id
            record.department_id = record.schedule_id.department_id

    name = fields.Char(
        "Name",
        size=64,
        required=True,
    )
    dayofweek = fields.Selection(
        DAYOFWEEK_SELECTION,
        'Day of Week',
        required=True,
        index=True,
        default='0'
    )
    date_start = fields.Datetime(
        'Start Date and Time',
        required=True,
    )
    date_end = fields.Datetime(
        'End Date and Time',
        required=True,
    )

    schedule_id = fields.Many2one(
        'hr.schedule',
        'Schedule',
        required=True,
    )
    department_id = fields.Many2one(
        'hr.department', compute='_compute_employee_id', string='Department', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')

    alert_ids = fields.One2many(
        'hr.schedule.alert', 'sched_detail_id', 'Alerts', readonly=True,)
    state = fields.Selection([('draft', 'Draft'),
                              ('validate', 'Confirmed'),
                              ('locked', 'Locked'),
                              ('unlocked', 'Unlocked'),
                              ],
                             required=True,
                             readonly=True,
                             default='draft')

    _order = 'schedule_id, date_start, dayofweek'

    @api.multi
    @api.constrains('date_start', 'date_end')
    def _detail_date(self):
        for dtl in self:
            self.env.cr.execute("""\
SELECT id
FROM hr_schedule_detail
WHERE (date_start <= %s and %s <= date_end)
  AND schedule_id=%s
  AND id <> %s""", (dtl.date_end, dtl.date_start, dtl.schedule_id.id, dtl.id))
            if self.env.cr.fetchall():
                raise ValidationError(
                    _('You cannot have scheduled days that overlap!'))
        return True

    def scheduled_hours_on_day(
            self, employee_id, contract_id, dt):
        dtDelta = timedelta(seconds=0)
        shifts = self.scheduled_begin_end_times(employee_id, dt)
        for start, end in shifts:
            dtDelta += end - start
        return float(dtDelta.seconds / 60) / 60.0

    def scheduled_begin_end_times(
            self, employee_id, dt):
        """Returns a list of tuples containing shift start and end
        times for the day
        """

        user_tz = timezone(self.env.user.tz)

        day = user_tz.localize(datetime(dt.year, dt.month, dt.day)).astimezone(utc)

        res = []
        detail_ids = self.search([
            ('schedule_id.employee_id.id', '=', employee_id),
            ('date_start', '>=', fields.Datetime.to_string(day)),
            ('date_start', '<', fields.Datetime.to_string(day + relativedelta(days=1))),
        ], order='date_start',)
        if len(detail_ids) > 0:
            for detail in detail_ids:
                res.append((
                    fields.Datetime.from_string(detail.date_start),
                    fields.Datetime.from_string(detail.date_end),
                ))

        return res

    def scheduled_hours_on_day_from_range(self, d, range_dict):

        dtDelta = timedelta(seconds=0)
        shifts = range_dict[fields.Date.to_string(d)]
        for start, end in shifts:
            dtDelta += end - start

        return float(dtDelta.seconds / 60) / 60.0

    def scheduled_begin_end_times_range(self, employee_id, dStart, dEnd):
        """Returns a dictionary with the dates in range dtStart - dtEnd
        as keys and a list of tuples containing shift start and end
        times during those days as values
        """

        res = {}
        d = dStart
        while d <= dEnd:
            res.update({fields.Date.to_string(d): []})
            d += timedelta(days=+1)

        detail_ids = self.search([
            ('schedule_id.employee_id.id', '=', employee_id),
            ('day', '>=', fields.Date.to_string(dStart)),
            ('day', '<=', fields.Date.to_string(dEnd)),
        ],
            order='date_start')
        if len(detail_ids) > 0:
            for detail in detail_ids:
                res[detail.day].append((
                    fields.Datetime.from_string(detail.date_start),
                    fields.Datetime.from_string(detail.date_end),
                ))

        return res

    @api.multi
    def remove_direct_alerts(self):
        """
        Remove alerts directly attached to the schedule detail
        """
        for shift in self:
            shift.alert_ids.unlink()

    @api.multi
    def create(self, vals):

        res = super(schedule_detail, self).create(vals)

        # res.compute_alerts()

        return res

    def unlink(self):

        detail_ids = self.filtered(lambda r: r.state in ['draft', 'unlocked'])

        # Remove alerts directly attached to the schedule details
        #
        detail_ids.remove_direct_alerts()

        res = super(schedule_detail, detail_ids).unlink()

        # Remove all alerts for the employee(s) for the day and recompute.
        #
        # self.compute_alerts()

        return res

    def write(self, vals):

        res = super(schedule_detail, self).write(vals)

        return res

    @api.multi
    def workflow_validate(self):
        self.write({'state': 'validate'})
        

    @api.multi
    def workflow_lock(self):
        self.write({'state': 'locked'})
        self.mapped('schedule_id').notify_lock()


    @api.multi
    def workflow_unlock(self):
        self.write({'state': 'unlocked'})
        self.mapped('schedule_id').notify_unlock()

    @api.multi
    def compute_alerts(self):
        alert_obj = self.env['hr.schedule.alert']

        for shift in self:
            alert_obj.compute_alerts_for_shift(shift)
