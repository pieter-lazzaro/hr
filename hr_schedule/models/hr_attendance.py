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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

from odoo import models, fields, api


class hr_attendance(models.Model):

    _name = 'hr.attendance'
    _inherit = 'hr.attendance'

    alert_ids = fields.One2many(
        'hr.schedule.alert',
        'punch_id',
        'Exceptions',
        readonly=True,
    )

    @api.multi
    def _remove_direct_alerts(self):
        """Remove alerts directly attached to the attendance and return
        a unique list of tuples of employee ids and attendance dates.
        """

        # Remove alerts directly attached to the attendances
        #
        attendances = []
        attendance_keys = []
        for attendance in self:
            attendance.alert_ids.unlink()
            key = str(attendance.employee_id.id) + attendance.day
            if key not in attendance_keys:
                attendances.append((attendance.employee_id.id, attendance.day))
                attendance_keys.append(key)

        return attendances

    @api.model
    def _recompute_alerts(self, attendances):
        """Recompute alerts for each record in attendances."""

        alert_obj = self.env['hr.schedule.alert']

        # Remove all alerts for the employee(s) for the day and recompute.
        #
        for employee_id, day in attendances:

            # Today's records will be checked tomorrow. Future records can't
            # generate alerts.
            if day >= fields.Date.context_today(self):
                continue

            # TODO - Someone who cares about DST should fix this
            #
            user_tz = self.env.user.tz
            dt = datetime.strptime(day + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
            lcldt = timezone(user_tz).localize(dt, is_dst=False)
            utcdt = lcldt.astimezone(utc)
            utcdtNextDay = utcdt + relativedelta(days=+1)
            strDayStart = utcdt.strftime('%Y-%m-%d %H:%M:%S')
            strNextDay = utcdtNextDay.strftime('%Y-%m-%d %H:%M:%S')

            alert_ids = alert_obj.search([
                ('employee_id', '=', employee_id),
                '&',
                ('name', '>=', strDayStart),
                ('name', '<', strNextDay)
            ])
            alert_ids.unlink()
            alert_obj.compute_alerts_by_employee(employee_id, day)

    @api.model
    def create(self, vals):

        res = super(hr_attendance, self).create(vals)

        attendances = [
            (
                res.employee_id.id, fields.Date.context_today(res)
            )
        ]
        self._recompute_alerts(attendances)

        return res

    @api.multi
    def unlink(self):

        # Remove alerts directly attached to the attendances
        #
        attendances = self._remove_direct_alerts()

        res = super(hr_attendance, self).unlink()

        # Remove all alerts for the employee(s) for the day and recompute.
        #
        self._recompute_alerts(attendances)

        return res

    @api.multi
    def write(self, vals):

        # Flag for checking wether we have to recompute alerts
        trigger_alert = False
        for k, v in vals.items():
            if k in ['name', 'action']:
                trigger_alert = True

        if trigger_alert:
            # Remove alerts directly attached to the attendances
            #
            attendances = self._remove_direct_alerts()

        res = super(hr_attendance, self).write(vals)

        if trigger_alert:
            # Remove all alerts for the employee(s) for the day and recompute.
            #
            self._recompute_alerts(attendances)

        return res
