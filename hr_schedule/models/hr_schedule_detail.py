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
from datetime import timedelta
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
            obj.day = fields.Date.from_string(obj.date_start)

    @api.depends('schedule_id')
    def _compute_employee_id(self):
        for record in self:
            record.employee_id = record.schedule_id.employee_id
            record.department_id = record.schedule_id.department_id

    def _get_ids_from_sched(self):
        res = []
        for sched in self.pool.get('hr.schedule').browse(
                cr, uid, ids, context=context):
            for detail in sched.detail_ids:
                res.append(detail.id)
        return res

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
    day = fields.Date(
        'Day',
        required=True,
        index=1,
        compute='_day_compute',
        store=True
    )
    schedule_id = fields.Many2one(
        'hr.schedule',
        'Schedule',
        required=True,
    )
    department_id = fields.Many2one(
        'hr.department', compute='_compute_employee_id', string='Department', store=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', store=True)

    alert_ids = fields.One2many(
        'hr.schedule.alert', 'sched_detail_id', 'Alerts', readonly=True,)
    state = fields.Selection([
        ('draft', 'Draft'),
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

        res = []
        detail_ids = self.search([
            ('schedule_id.employee_id.id', '=', employee_id),
            ('day', '=', dt.strftime(
                '%Y-%m-%d')),
        ],
            order='date_start',)
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
    def _remove_direct_alerts(self):
        """Remove alerts directly attached to the schedule detail and
        return a unique list of tuples of employee id and schedule
        detail date.
        """

        alert_obj = self.env['hr.schedule.alert']

        # Remove alerts directly attached to these schedule details
        #
        alert_ids = []
        scheds = []
        sched_keys = []
        for sched_detail in self:

            [alert_ids.append(alert.id) for alert in sched_detail.alert_ids]

            # Hmm, creation of this record triggers a workflow action that
            # tries to write to it. But it seems that computed fields aren't
            # available at this stage. So, use a fallback and compute the day
            # ourselves.
            day = sched_detail.day
            if not sched_detail.day:
                day = time.strftime('%Y-%m-%d', time.strptime(
                    sched_detail.date_start, '%Y-%m-%d %H:%M:%S'))
            key = str(sched_detail.schedule_id.employee_id.id) + day
            if key not in sched_keys:
                scheds.append((sched_detail.schedule_id.employee_id.id, day))
                sched_keys.append(key)

        if len(alert_ids) > 0:
            alert_obj.browse(alert_ids).unlink()

        return scheds

    def _recompute_alerts(self, attendances):
        """Recompute alerts for each record in schedule detail."""

        alert_obj = self.env['hr.schedule.alert']

        # Remove all alerts for the employee(s) for the day and recompute.
        #
        for ee_id, strDay in attendances:

            # Today's records will be checked tomorrow. Future records can't
            # generate alerts.
            if strDay >= fields.Date.context_today(self):
                continue

            # TODO - Someone who cares about DST should fix this
            #
            user_tz = self.env.user.tz
            dt = fields.Datetime.from_string(strDay)
            lcldt = timezone(user_tz).localize(dt, is_dst=False)
            utcdt = lcldt.astimezone(utc)
            utcdtNextDay = utcdt + relativedelta(days=+1)
            strDayStart = fields.Datetime.to_string(utcdt)
            strNextDay = fields.Datetime.to_string(utcdtNextDay)

            alert_ids = alert_obj.search([
                ('employee_id', '=', ee_id),
                '&',
                ('name', '>=', strDayStart),
                ('name', '<', strNextDay)
            ])
            alert_ids.unlink()
            alert_obj.compute_alerts_by_employee(ee_id, strDay)

    def create(self, vals):

        if 'day' not in vals and 'date_start' in vals:
            # TODO - Someone affected by DST should fix this
            #
            user_tz = timezone(self.env.user.tz)
            dtStart = fields.Datetime.from_string(vals['date_start'])
            locldtStart = user_tz.localize(dtStart, is_dst=False)
            utcdtStart = locldtStart.astimezone(utc)
            dDay = utcdtStart.astimezone(user_tz).date()
            vals.update({'day': dDay})

        res = super(schedule_detail, self).create(vals)

        attendances = [
            (
                res.schedule_id.employee_id.id, fields.Date.context_today(
                    self),
            ),
        ]
        self._recompute_alerts(attendances)

        return res

    def unlink(self):

        detail_ids = self.filtered(lambda r: r.state in ['draft', 'unlocked'])

        # Remove alerts directly attached to the schedule details
        #
        attendances = detail_ids._remove_direct_alerts()

        res = super(schedule_detail, detail_ids).unlink()

        # Remove all alerts for the employee(s) for the day and recompute.
        #
        self._recompute_alerts(attendances)

        return res

    def write(self, vals):

        # Flag for checking wether we have to recompute alerts
        trigger_alert = False
        for k, v in vals.items():
            if k in ['date_start', 'date_end']:
                trigger_alert = True

        if trigger_alert:
            # Remove alerts directly attached to the attendances
            #
            attendances = self._remove_direct_alerts()

        res = super(schedule_detail, self).write(vals)

        if trigger_alert:
            # Remove all alerts for the employee(s) for the day and recompute.
            #
            self._recompute_alerts(attendances)

        return res

    def workflow_validate(self):
        self.state = 'validate'

    def workflow_lock(self):
        for detail in self:
            detail.write({'state': 'locked'})
            detail.schedule_id.workflow_lock()

    def workflow_unlock(self):
        for detail in self:
            detail.write({'state': 'unlocked'})
            detail.schedule_id.workflow_unlock()
