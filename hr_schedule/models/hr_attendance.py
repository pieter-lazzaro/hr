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

from odoo import models, fields

class hr_attendance(models.Model):

    _name = 'hr.attendance'
    _inherit = 'hr.attendance'

    alert_ids = fields.One2many(
        'hr.schedule.alert',
        'punch_id',
        'Exceptions',
        readonly=True,
    )

    def _remove_direct_alerts(self, cr, uid, ids, context=None):
        """Remove alerts directly attached to the attendance and return
        a unique list of tuples of employee ids and attendance dates.
        """

        alert_obj = self.pool.get('hr.schedule.alert')

        # Remove alerts directly attached to the attendances
        #
        alert_ids = []
        attendances = []
        attendance_keys = []
        for attendance in self.browse(cr, uid, ids, context=context):
            [alert_ids.append(alert.id) for alert in attendance.alert_ids]
            key = str(attendance.employee_id.id) + attendance.day
            if key not in attendance_keys:
                attendances.append((attendance.employee_id.id, attendance.day))
                attendance_keys.append(key)

        if len(alert_ids) > 0:
            alert_obj.unlink(cr, uid, alert_ids, context=context)

        return attendances

    def _recompute_alerts(self, cr, uid, attendances, context=None):
        """Recompute alerts for each record in attendances."""

        alert_obj = self.pool.get('hr.schedule.alert')

        # Remove all alerts for the employee(s) for the day and recompute.
        #
        for ee_id, strDay in attendances:

            # Today's records will be checked tomorrow. Future records can't
            # generate alerts.
            if strDay >= fields.Date.context_today(
                    self, cr, uid, context=context):
                continue

            # TODO - Someone who cares about DST should fix this
            #
            data = self.pool.get('res.users').read(
                cr, uid, uid, ['tz'], context=context)
            dt = datetime.strptime(strDay + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
            lcldt = timezone(data['tz']).localize(dt, is_dst=False)
            utcdt = lcldt.astimezone(utc)
            utcdtNextDay = utcdt + relativedelta(days=+1)
            strDayStart = utcdt.strftime('%Y-%m-%d %H:%M:%S')
            strNextDay = utcdtNextDay.strftime('%Y-%m-%d %H:%M:%S')

            alert_ids = alert_obj.search(
                cr, uid, [
                    ('employee_id', '=', ee_id),
                    '&',
                    ('name', '>=', strDayStart),
                    ('name', '<', strNextDay)
                ], context=context)
            alert_obj.unlink(cr, uid, alert_ids, context=context)
            alert_obj.compute_alerts_by_employee(
                cr, uid, ee_id, strDay, context=context)

    def create(self, cr, uid, vals, context=None):

        res = super(hr_attendance, self).create(cr, uid, vals, context=context)

        obj = self.browse(cr, uid, res, context=context)
        attendances = [
            (
                obj.employee_id.id, fields.Date.context_today(
                    self, cr, uid, context=context
                )
            )
        ]
        self._recompute_alerts(cr, uid, attendances, context=context)

        return res

    def unlink(self, cr, uid, ids, context=None):

        # Remove alerts directly attached to the attendances
        #
        attendances = self._remove_direct_alerts(cr, uid, ids, context=context)

        res = super(hr_attendance, self).unlink(cr, uid, ids, context=context)

        # Remove all alerts for the employee(s) for the day and recompute.
        #
        self._recompute_alerts(cr, uid, attendances, context=context)

        return res

    def write(self, cr, uid, ids, vals, context=None):

        # Flag for checking wether we have to recompute alerts
        trigger_alert = False
        for k, v in vals.iteritems():
            if k in ['name', 'action']:
                trigger_alert = True

        if trigger_alert:
            # Remove alerts directly attached to the attendances
            #
            attendances = self._remove_direct_alerts(
                cr, uid, ids, context=context)

        res = super(hr_attendance, self).write(
            cr, uid, ids, vals, context=context)

        if trigger_alert:
            # Remove all alerts for the employee(s) for the day and recompute.
            #
            self._recompute_alerts(cr, uid, attendances, context=context)

        return res
