# -*- coding:utf-8 -*-
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
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

from odoo import fields, models, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from odoo.tools.translate import _

from ..models.week_days import DAYOFWEEK_SELECTION

import logging
_l = logging.getLogger(__name__)


class restday(models.TransientModel):

    _name = 'hr.restday.wizard'
    _description = 'Schedule Template Change Wizard'

    employee_id = fields.Many2one(
        'hr.employee',
        'Employee',
        required=True,
    )
    contract_id = fields.Many2one(
        'hr.contract', related='employee_id.contract_id', string='Contract', readonly=True)
    st_current_id = fields.Many2one(
        'hr.schedule.template',
        'Current Template',
        readonly=True,
    )
    st_new_id = fields.Many2one(
        'hr.schedule.template',
        'New Template',
    )
    permanent = fields.Boolean(
        'Make Permanent',
    )
    temp_restday = fields.Boolean(
        'Temporary Rest Day Change',
        help="If selected, change the rest day to the specified day only "
        "for the selected schedule.",
        default=False
    )
    dayofweek = fields.Selection(
        DAYOFWEEK_SELECTION,
        'Rest Day',
        index=True,
    )
    temp_week_start = fields.Date(
        'Start of Week',
    )
    week_start = fields.Date(
        'Start of Week',
    )

    @api.onchange('employee_id')
    def onchange_employee(self):

        if self.employee_id:
            self.st_current_id = self.employee_id.contract_id.schedule_template_id.id


    @api.onchange('week_start')
    def onchange_week(self):

        if self.week_start:
            d = datetime.strptime(self.week_start, "%Y-%m-%d")
            if d.weekday() != 0:
                self.week_start = False

    @api.onchange('temp_week_start')
    def onchange_temp_week(self):

        if self.temp_week_start:
            d = datetime.strptime(self.temp_week_start, "%Y-%m-%d")
            if d.weekday() != 0:
                self.temp_week_start = False
                

    def _create_detail(
        self, schedule, actual_dayofweek, template_dayofweek,
            week_start):

        # First, see if there's a schedule for the actual dayofweek.
        # If so, use it.
        #
        for worktime in schedule.template_id.worktime_ids:
            if worktime.dayofweek == actual_dayofweek:
                template_dayofweek = actual_dayofweek

        prevutcdtStart = False
        prevDayofWeek = False
        user = self.env.user
        local_tz = timezone(user.tz)
        dSchedStart = datetime.strptime(schedule.date_start, OE_DFORMAT).date()
        dWeekStart = schedule.date_start < week_start and datetime.strptime(
            week_start, OE_DFORMAT).date() or dSchedStart

        for worktime in schedule.template_id.worktime_ids:

            if worktime.dayofweek != template_dayofweek:
                continue

            from_hour, from_minute = divmod(worktime.hour_from * 60, 60)
            to_hour, to_minute = divmod(worktime.hour_to * 60, 60)
            
            # TODO - Someone affected by DST should fix this
            #
            dtStart = datetime.strptime(
                dWeekStart.strftime('%Y-%m-%d') + ' ' + from_hour + ':' + from_minute +
                ':00', '%Y-%m-%d %H:%M:%S'
            )
            locldtStart = local_tz.localize(dtStart, is_dst=False)
            utcdtStart = locldtStart.astimezone(utc)
            if actual_dayofweek != '0':
                utcdtStart = utcdtStart + \
                    relativedelta(days=+int(actual_dayofweek))
            dDay = utcdtStart.astimezone(local_tz).date()

            # If this worktime is a continuation (i.e - after lunch) set the
            # start time based on the difference from the previous record
            #
            if prevDayofWeek and prevDayofWeek == actual_dayofweek:
                prevHour = prevutcdtStart.strftime('%H')
                prevMin = prevutcdtStart.strftime('%M')
                curHour = utcdtStart.strftime('%H')
                curMin = utcdtStart.strftime('%M')
                delta_seconds = (
                    datetime.strptime(curHour + ':' + curMin, '%H:%M') -
                    datetime.strptime(prevHour + ':' + prevMin, '%H:%M')
                ).seconds
                utcdtStart = prevutcdtStart + timedelta(seconds=+delta_seconds)
                dDay = prevutcdtStart.astimezone(local_tz).date()

            delta_seconds = (
                datetime.strptime(to_hour + ':' + to_minute, '%H:%M') -
                datetime.strptime(from_hour + ':' + from_minute, '%H:%M')
            ).seconds
            utcdtEnd = utcdtStart + timedelta(seconds=+delta_seconds)

            val = {
                'name': schedule.name,
                'dayofweek': actual_dayofweek,
                'day': dDay,
                'date_start': utcdtStart.strftime('%Y-%m-%d %H:%M:%S'),
                'date_end': utcdtEnd.strftime('%Y-%m-%d %H:%M:%S'),
                'schedule_id': schedule.id,
            }
            schedule.write({
                    'detail_ids': [(0, 0, val)],
                })

            prevDayofWeek = worktime.dayofweek
            prevutcdtStart = utcdtStart

    def _change_restday(self, employee_id, week_start, dayofweek):

        sched_obj = self.env['hr.schedule']
        sched_detail_obj = self.env['hr.schedule.detail']

        sched = sched_obj.search([('employee_id', '=', employee_id),
                      ('date_start', '<=', week_start),
                      ('date_end', '>=', week_start),
                      ('state', 'not in', ['locked'])], limit=1)
        dtFirstDay = datetime.strptime(
            sched.detail_ids[0].date_start, OE_DTFORMAT)
        date_start = (
            dtFirstDay.strftime(OE_DFORMAT) < week_start
            and week_start + ' ' + dtFirstDay.strftime('%H:%M:%S')
            or dtFirstDay.strftime(OE_DTFORMAT)
        )
        dtNextWeek = datetime.strptime(
            date_start, OE_DTFORMAT) + relativedelta(weeks=+1)

        # First get the current rest days
        rest_days = sched.get_rest_days(dtFirstDay.strftime(OE_DFORMAT))

        # Next, remove the schedule detail for the new rest day
        for dtl in sched.detail_ids:
            if (dtl.date_start < week_start
                    or datetime.strptime(dtl.date_start, OE_DTFORMAT)
                    >= dtNextWeek):
                continue
            if dtl.dayofweek == dayofweek:
                dtl.unlink()

        # Enter the new rest day(s)
        #
        sched_obj = self.env['hr.schedule']
        nrest_days = [dayofweek] + rest_days[1:]
        dSchedStart = datetime.strptime(sched.date_start, OE_DFORMAT).date()
        dWeekStart = sched.date_start < week_start and datetime.strptime(
            week_start, OE_DFORMAT).date() or dSchedStart
        if dWeekStart == dSchedStart:
            sched.add_restdays('restday_ids1', rest_days=nrest_days,)
        elif dWeekStart == dSchedStart + relativedelta(days=+7):
            sched.add_restdays('restday_ids2', rest_days=nrest_days)
        elif dWeekStart == dSchedStart + relativedelta(days=+14):
            sched.add_restdays('restday_ids3', rest_days=nrest_days)
        elif dWeekStart == dSchedStart + relativedelta(days=+21):
            sched.add_restdays('restday_ids4', rest_days=nrest_days)
        elif dWeekStart == dSchedStart + relativedelta(days=+28):
            sched.add_restdays('restday_ids5', rest_days=nrest_days)

        # Last, add a schedule detail for the first rest day in the week using
        # the template for the new (temp) rest day
        #
        if len(rest_days) > 0:
            self._create_detail(sched, str(rest_days[0]), dayofweek, week_start)

    def _remove_add_schedule(self, schedule_id, week_start, tpl_id):
        """Remove the current schedule and add a new one in its place
        according to the new template. If the week that the change
        starts in is not at the beginning of a schedule create two
        new schedules to accommodate the truncated old one and the
        partial new one.
        """

        sched_obj = self.env['hr.schedule']
        sched = sched_obj.browse(schedule_id)

        vals2 = False
        vals1 = {
            'name': sched.name,
            'employee_id': sched.employee_id.id,
            'template_id': tpl_id,
            'date_start': sched.date_start,
            'date_end': sched.date_end,
        }

        if week_start > sched.date_start:
            dWeekStart = datetime.strptime(week_start, '%Y-%m-%d').date()
            start_day = dWeekStart.strftime('%Y-%m-%d')
            vals1['template_id'] = sched.template_id.id
            vals1['date_end'] = (
                dWeekStart + relativedelta(days=-1)).strftime('%Y-%m-%d')
            vals2 = {
                'name': (sched.employee_id.name + ': ' + start_day + ' Wk ' +
                         str(dWeekStart.isocalendar()[1])),
                'employee_id': sched.employee_id.id,
                'template_id': tpl_id,
                'date_start': start_day,
                'date_end': sched.date_end,
            }

        sched.unlink()
        _l.warning('vals1: %s', vals1)
        sched_obj.create(vals1)
        if vals2:
            _l.warning('vals2: %s', vals2)
            sched_obj.create(vals2)

    def _change_by_template(self, employee_id, week_start, new_template_id, doall):

        sched_obj = self.env['hr.schedule']

        schedule_ids = sched_obj.search([('employee_id', '=', employee_id),
                      ('date_start', '<=', week_start),
                      ('date_end', '>=', week_start),
                      ('state', 'not in', ['locked'])])

        # Remove the current schedule and add a new one in its place according
        # to the new template
        #
        if len(schedule_ids) > 0:
            self._remove_add_schedule(schedule_ids[0].id, week_start, new_template_id)

        # Also, change all subsequent schedules if so directed
        if doall:
            ids = sched_obj.search([
                    ('employee_id', '=', employee_id),
                    ('date_start', '>', week_start),
                    ('state', 'not in', ['locked'])
                ])
            for i in ids:
                self._remove_add_schedule(i.id, week_start, new_template_id)

    def change_restday(self):

        # Change the rest day for only one schedule
        if (self.temp_restday
                and self.dayofweek
                and self.temp_week_start):
            self._change_restday(self.employee_id, self.temp_week_start,self.dayofweek)

        # Change entire week's schedule to the chosen schedule template
        if (not self.temp_restday
                and self.st_new_id
                and self.week_start):

            if self.week_start:
                self._change_by_template(self.employee_id.id, self.week_start,
                    self.st_new_id.id, self.permanent)

            # If this change is permanent modify employee's contract to
            # reflect the new template
            #
            if self.permanent:
                self.contract_id.schedule_template_id = self.st_new_id

        return {
            'name': 'Change Schedule Template',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.restday.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.env.context
        }
