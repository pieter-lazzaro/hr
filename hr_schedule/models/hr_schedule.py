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

import time


from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from odoo.tools.translate import _
from odoo.exceptions import ValidationError, UserError

import logging
_logger = logging.getLogger(__name__)


class hr_schedule(models.Model):

    _name = 'hr.schedule'
    _inherit = ['mail.thread']
    _description = 'Employee Schedule'

    @api.depends('detail_ids')
    def _compute_alerts(self):
        for obj in self:
            alert_ids = []
            for detail in obj.detail_ids:
                [alert_ids.append(a.id) for a in detail.alert_ids]
            obj.alert_ids = alert_ids

    name = fields.Char(
        "Description",
        size=64,
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        readonly=True,
        default=lambda self: self.env.user.company_id.id
    )
    employee_id = fields.Many2one(
        'hr.employee',
        'Employee',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    template_id = fields.Many2one(
        'hr.schedule.template',
        'Schedule Template',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    detail_ids = fields.One2many(
        'hr.schedule.detail',
        'schedule_id',
        'Schedule Detail',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    date_start = fields.Date(
        'Start Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    date_end = fields.Date(
        'End Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True, store=True)

    alert_ids = fields.One2many(
        'hr.schedule.alert',
        compute="_compute_alerts",
        string='Alerts',
        method=True,
        readonly=True)

    restday_ids1 = fields.Many2many(
        'hr.schedule.weekday',
        'schedule_restdays_rel1',
        'sched_id',
        'weekday_id',
        string='Rest Days Week 1',
    )
    restday_ids2 = fields.Many2many(
        'hr.schedule.weekday',
        'schedule_restdays_rel2',
        'sched_id',
        'weekday_id',
        string='Rest Days Week 2',
    )
    restday_ids3 = fields.Many2many(
        'hr.schedule.weekday',
        'schedule_restdays_rel3',
        'sched_id',
        'weekday_id',
        string='Rest Days Week 3',
    )
    restday_ids4 = fields.Many2many(
        'hr.schedule.weekday',
        'schedule_restdays_rel4',
        'sched_id',
        'weekday_id',
        string='Rest Days Week 4',
    )
    restday_ids5 = fields.Many2many(
        'hr.schedule.weekday',
        'schedule_restdays_rel5',
        'sched_id',
        'weekday_id',
        string='Rest Days Week 5',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('validate', 'Confirmed'),
            ('locked', 'Locked'),
            ('unlocked', 'Unlocked'),
        ],
        'State',
        required=True,
        readonly=True,
        default='draft'
    )

    @api.depends('employee_id')
    def _compute_department_id(self):
        if self.employee_id.department_id:
            self.department_id = self.employee_id.department_id

    @api.constrains('date_start', 'date_end')
    def _schedule_date(self):
        for shd in self:
            self.env.cr.execute("""\
SELECT id
FROM hr_schedule
WHERE (date_start <= %s and %s <= date_end)
  AND employee_id=%s
  AND id <> %s""", (shd.date_end, shd.date_start, shd.employee_id.id, shd.id))
            if self.env.cr.fetchall():
                raise ValidationError(
                    _('You cannot have schedules that overlap!'))

    def get_rest_days_for_employee(self, employee_id, dt):
        """If the rest day(s) have been explicitly specified that's
        what is returned, otherwise a guess is returned based on the
        week days that are not scheduled. If an explicit rest day(s)
        has not been specified an empty list is returned. If it is able
        to figure out the rest days it will return a list of week day
        integers with Monday being 0.
        """

        day = fields.Date.to_string(dt)
        schedules = self.search([
            ('employee_id', '=', employee_id),
            ('date_start', '<=', day),
            ('date_end', '>=', day),
        ])

        if len(schedules) == 0:
            return None

        elif len(schedules) > 1:
            raise UserError(_('Programming Error') + _(
                'Employee has a scheduled date in more than one schedule.'))

        # If the day is in the middle of the week get the start of the week
        if dt.weekday() == 0:
            week_start = fields.Date.to_string(dt)
        else:
            week_start = (
                dt + relativedelta(days=-dt.weekday())).strftime(OE_DFORMAT)

        return schedules.get_rest_days(week_start)

    def get_rest_days(self, week_start):
        """If the rest day(s) have been explicitly specified that's
        what is returned, otherwise a guess is returned based on the
        week days that are not scheduled. If an explicit rest day(s)
        has not been specified an empty list is returned. If it is
        able to figure out the rest days it will return a list of week
        day integers with Monday being 0.
        """

        res = []

        # Set the boundaries of the week (i.e- start of current week and start
        # of next week)
        #
        if not self.detail_ids:
            return res

        date_first_day = fields.Date.from_string(self.detail_ids[0].date_start)
        date_week_start = fields.Date.from_string(week_start)

        date_start = date_week_start

        if date_first_day > date_week_start:
            date_start = date_first_day

        # date_start = date_first_day.strftime(OE_DFORMAT) < week_start \
        #     and week_start + ' ' + date_first_day.strftime(
        #         '%H:%M:%S') or date_first_day.strftime(OE_DTFORMAT)
        date_next_week = fields.Date.from_string(
            date_start) + relativedelta(weeks=+1)

        # Determine the appropriate rest day list to use
        #
        restday_ids = False
        date_scheduled_start = fields.Date.from_string(self.date_start)
        if date_week_start == date_scheduled_start:
            restday_ids = self.restday_ids1
        elif date_week_start == date_scheduled_start + relativedelta(days=+7):
            restday_ids = self.restday_ids2
        elif date_week_start == date_scheduled_start + relativedelta(days=+14):
            restday_ids = self.restday_ids3
        elif date_week_start == date_scheduled_start + relativedelta(days=+21):
            restday_ids = self.restday_ids4
        elif date_week_start == date_scheduled_start + relativedelta(days=+28):
            restday_ids = self.restday_ids5

        # If there is explicit rest day data use it, otherwise try to guess
        # based on which days are not scheduled.
        #
        res = []
        if restday_ids:
            res = [rd.sequence for rd in restday_ids]
        else:
            weekdays = ['0', '1', '2', '3', '4', '5', '6']
            scheddays = []
            for dtl in self.detail_ids:
                # Make sure the date we're examining isn't in the previous week
                # or the next one
                if dtl.date_start < week_start or fields.Date.from_string(dtl.date_start) >= date_next_week:
                    continue
                if dtl.dayofweek not in scheddays:
                    scheddays.append(dtl.dayofweek)
            res = [int(d) for d in weekdays if d not in scheddays]
            # If there are no sched.details return nothing instead of *ALL* the
            # days in the week
            if len(res) == 7:
                res = []

        return res

    @api.onchange('date_start', 'employee_id')
    def onchange_start_date(self):

        if self.date_start:
            date_start = fields.Date.from_string(self.date_start)
            # The schedule must start on a Monday
            if date_start.weekday() != 0:
                self.date_start = False
                self.date_end = False
            else:
                date_end = date_start + relativedelta(days=+6)
                self.date_end = fields.Date.to_string(date_end)

        if not self.employee_id:
            return

        if self.employee_id.name:
            self.name = self.employee_id.name
            if self.date_start:
                date_start = fields.Date.from_string(self.date_start)
                self.name = self.name + ': ' + \
                    self.date_start + ' Wk ' + \
                    str(date_start.isocalendar()[1])

        if self.employee_id.department_id:
            self.department_id = self.employee_id.department_id

        if self.employee_id.contract_id:
            if self.employee_id.contract_id.schedule_template_id:
                self.template_id = self.employee_id.contract_id.schedule_template_id

    @api.multi
    def delete_details(self):
        for schedule in self:
            schedule.detail_ids.unlink()

    def add_restdays(self, field_name, rest_days=None):
        self.ensure_one()
        restday_ids = []
        if rest_days is None:
            for rd in self.template_id.restday_ids:
                restday_ids.append(rd.id)
        else:
            restday_ids = self.env['hr.schedule.weekday'].search([
                ('sequence', 'in', rest_days)
            ])
        if len(restday_ids) > 0:
            self.write({field_name: [(6, 0, restday_ids)]})

        return

    @api.multi
    def create_details(self):
        leave_obj = self.env['hr.holidays']

        for schedule in self:
            if schedule.template_id:

                # Get first day of contract
                dContract = False
                for c in schedule.employee_id.contract_ids:
                    d = datetime.strptime(c.date_start, OE_DFORMAT).date()
                    if not dContract or d < dContract:
                        dContract = d

                leaves = []
                leave_ids = leave_obj.search(
                    [('employee_id', '=', schedule.employee_id.id),
                     ('date_from', '<=',
                      schedule.date_end), ('date_to', '>=',
                                           schedule.date_start),
                     ('state', 'in', ['draft', 'validate', 'validate1'])])
                for lv in leave_ids:
                    utcdtFrom = utc.localize(
                        datetime.strptime(lv.date_from, OE_DTFORMAT),
                        is_dst=False)
                    utcdtTo = utc.localize(
                        datetime.strptime(lv.date_to, OE_DTFORMAT),
                        is_dst=False)
                    leaves.append((utcdtFrom, utcdtTo))

                local_tz = timezone(self.env.user.tz)
                dCount = datetime.strptime(schedule.date_start,
                                           '%Y-%m-%d').date()
                dCountEnd = datetime.strptime(schedule.date_end,
                                              '%Y-%m-%d').date()
                dWeekStart = dCount
                dSchedStart = dCount
                while dCount <= dCountEnd:

                    # Enter the rest day(s)
                    #
                    if dCount == dSchedStart:
                        self.add_restdays(schedule, self.restday_ids1)
                    elif dCount == dSchedStart + relativedelta(days=+7):
                        self.add_restdays(schedule, self.restday_ids2)
                    elif dCount == dSchedStart + relativedelta(days=+14):
                        self.add_restdays(schedule, self.restday_ids3)
                    elif dCount == dSchedStart + relativedelta(days=+21):
                        self.add_restdays(schedule, self.restday_ids4)
                    elif dCount == dSchedStart + relativedelta(days=+28):
                        self.add_restdays(schedule, self.restday_ids5)

                    utcdtPrevOut = False
                    for worktime in schedule.template_id.worktime_ids:
    
                        from_hour, from_minute = divmod(
                            worktime.hour_from * 60, 60)
                        to_hour, to_minute = divmod(worktime.hour_to * 60, 60)

                        # XXX - Someone affected by DST should fix this
                        #
                        time_format = '{:.0f}:{:.0f}:00'

                        dTemp = dWeekStart + \
                            relativedelta(days=+(int(worktime.dayofweek)))
                        dtStart = datetime.strptime(
                            dTemp.strftime('%Y-%m-%d') + ' ' +
                            time_format.format(from_hour, from_minute),
                            OE_DTFORMAT)
                        locldtStart = local_tz.localize(dtStart, is_dst=False)
                        utcdtStart = locldtStart.astimezone(utc)
                        dDay = utcdtStart.astimezone(local_tz).date()

                        dtEnd = datetime.strptime(
                            dTemp.strftime('%Y-%m-%d') + ' ' +
                            time_format.format(to_hour, to_minute),
                            OE_DTFORMAT)
                        locldtEnd = local_tz.localize(dtEnd, is_dst=False)
                        utcdtEnd = locldtEnd.astimezone(utc)
                        if utcdtEnd < utcdtStart:
                            utcdtEnd += relativedelta(days=+1)

                        # If this record appears to be before the previous record it means the
                        # shift continues into the next day
                        if utcdtPrevOut and utcdtStart < utcdtPrevOut:
                            utcdtStart += relativedelta(days=+1)
                            utcdtEnd += relativedelta(days=+1)

                        # Skip days before start of contract
                        _d_str = utcdtStart.astimezone(local_tz).strftime(
                            OE_DFORMAT)
                        _d = datetime.strptime(_d_str, OE_DFORMAT).date()
                        if dContract and dContract > _d:
                            continue

                        # Leave empty holes where there are leaves
                        #
                        _skip = False
                        for utcdtFrom, utcdtTo in leaves:
                            if utcdtFrom <= utcdtStart and utcdtTo >= utcdtEnd:
                                _skip = True
                                break
                            elif utcdtFrom > utcdtStart and utcdtFrom <= utcdtEnd:
                                if utcdtTo == utcdtEnd:
                                    _skip = True
                                else:
                                    utcdtEnd = utcdtFrom + timedelta(
                                        seconds=-1)
                                break
                            elif utcdtTo >= utcdtStart and utcdtTo < utcdtEnd:
                                if utcdtTo == utcdtEnd:
                                    _skip = True
                                else:
                                    utcdtStart = utcdtTo + timedelta(
                                        seconds=+1)
                                break

                        # Do not recreate details that have not been deleted because
                        # they are locked.
                        #
                        for detail in schedule.detail_ids:
                            if detail.day == dDay.strftime(OE_DFORMAT) and              \
                                    utcdtStart.strftime(OE_DTFORMAT) >= detail.date_start and \
                                    utcdtStart.strftime(OE_DTFORMAT) <= detail.date_end:
                                _skip = True
                                break

                        if not _skip:
                            val = {
                                'name':
                                schedule.name,
                                'dayofweek':
                                worktime.dayofweek,
                                'day':
                                dDay,
                                'date_start':
                                utcdtStart.strftime('%Y-%m-%d %H:%M:%S'),
                                'date_end':
                                utcdtEnd.strftime('%Y-%m-%d %H:%M:%S'),
                                'schedule_id':
                                schedule.id,
                            }
                            schedule.write({'detail_ids': [(0, 0, val)]})

                        utcdtPrevOut = utcdtEnd

                    dCount = dWeekStart + relativedelta(weeks=+1)
                    dWeekStart = dCount

    def create(self, vals):

        my_id = super(hr_schedule, self).create(vals)
        my_id.create_details()

        return my_id

    def create_mass_schedule(self):
        """Creates tentative schedules for all employees based on the
        schedule template attached to their contract. Called from the
        scheduler.
        """

        sched_obj = self.env['hr.schedule']
        ee_obj = self.env['hr.employee']

        # Create a two-week schedule beginning from Monday of next week.
        #
        dt = datetime.today()
        days = 7 - dt.weekday()
        dt += relativedelta(days=+days)
        dStart = dt.date()
        dEnd = dStart + relativedelta(weeks=+2, days=-1)

        # Create schedules for each employee in each department
        #
        dept_ids = self.env['hr.department'].search([])
        for dept in self.env['hr.department'].browse(dept_ids):
            ee_ids = ee_obj.search(
                [
                    ('department_id', '=', dept.id),
                ], order="name")
            if len(ee_ids) == 0:
                continue

            for ee in ee_obj:

                if not ee.contract_id or not ee.contract_id.schedule_template_id:
                    continue

                # If there are overlapping schedules, don't create
                #
                overlap_sched_ids = sched_obj.search(
                    [('employee_id', '=', ee.id), ('date_start', '<=',
                                                   dEnd.strftime('%Y-%m-%d')),
                     ('date_end', '>=', dStart.strftime('%Y-%m-%d'))])
                if len(overlap_sched_ids) > 0:
                    continue

                sched = {
                    'name':
                    ee.name + ': ' + dStart.strftime('%Y-%m-%d') + ' Wk ' +
                    str(dStart.isocalendar()[1]),
                    'employee_id':
                    ee.id,
                    'template_id':
                    ee.contract_id.schedule_template_id.id,
                    'date_start':
                    dStart.strftime('%Y-%m-%d'),
                    'date_end':
                    dEnd.strftime('%Y-%m-%d'),
                }
                sched_obj.create(sched)

    def deletable(self):

        for schedule in self:
            if schedule.state not in ['draft', 'unlocked']:
                return False
            for detail in schedule.detail_ids:
                if detail.state not in ['draft', 'unlocked']:
                    return False

        return True

    @api.multi
    def unlink(self):

        for schedule in self:
            # Do not remove schedules that are not in draft or unlocked state
            if not self.deletable():
                continue

            # Delete the schedule details associated with this schedule
            #
            if len(schedule.detail_ids) > 0:
                schedule.detail_ids.unlink()

        return super(hr_schedule, self).unlink()

    @api.multi
    def workflow_validate(self):
        for sched in self:
            for detail in sched.detail_ids:
                detail.workflow_validate()
            self.state = 'validate'

    @api.multi
    def details_locked(self):
        for sched in self:
            for detail in sched.detail_ids:
                if detail.state != 'locked':
                    return False
        return True

    @api.multi
    def workflow_lock(self):
        '''Lock the Schedule Record. Expects to be called by its schedule detail
        records as they are locked one by one.  When the last one has been locked
        the schedule will also be locked.'''

        all_locked = True
        for sched in self:
            if sched.details_locked():
                sched.state = 'locked'
            else:
                all_locked = False

        return all_locked

    @api.multi
    def workflow_unlock(self):
        '''Unlock the Schedule Record. Expects to be called by its schedule detail
        records as they are unlocked one by one.  When the first one has been unlocked
        the schedule will also be unlocked.'''

        all_locked = True
        for sched in self:
            if not sched.details_locked():
                sched.state = 'unlocked'
            else:
                all_locked = False

        return not all_locked
