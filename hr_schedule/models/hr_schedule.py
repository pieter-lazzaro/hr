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
    )

    _defaults = {
        'company_id': (
            lambda self, cr, uid, context:
            self.pool.get('res.company')._company_default_get(
                cr, uid, 'hr.schedule', context=context
            )
        ),
        'state': 'draft',
    }

    def _schedule_date(self, cr, uid, ids, context=None):
        for shd in self.browse(cr, uid, ids, context=context):
            cr.execute("""\
SELECT id
FROM hr_schedule
WHERE (date_start <= %s and %s <= date_end)
  AND employee_id=%s
  AND id <> %s""", (shd.date_end, shd.date_start, shd.employee_id.id, shd.id))
            if cr.fetchall():
                return False
        return True

    def _rec_message(self, cr, uid, ids, context=None):
        return _('You cannot have schedules that overlap!')

    _constraints = [
        (_schedule_date, _rec_message, ['date_start', 'date_end']),
    ]

    def get_rest_days(self, cr, uid, employee_id, dt, context=None):
        """If the rest day(s) have been explicitly specified that's
        what is returned, otherwise a guess is returned based on the
        week days that are not scheduled. If an explicit rest day(s)
        has not been specified an empty list is returned. If it is able
        to figure out the rest days it will return a list of week day
        integers with Monday being 0.
        """

        day = dt.strftime(OE_DTFORMAT)
        ids = self.search(
            cr, uid, [
                ('employee_id', '=', employee_id),
                ('date_start', '<=', day),
                ('date_end', '>=', day),
            ], context=context)
        if len(ids) == 0:
            return None
        elif len(ids) > 1:
            raise models.except_orm(_('Programming Error'), _(
                'Employee has a scheduled date in more than one schedule.'))

        # If the day is in the middle of the week get the start of the week
        if dt.weekday() == 0:
            week_start = dt.strftime(OE_DFORMAT)
        else:
            week_start = (
                dt + relativedelta(days=-dt.weekday())).strftime(OE_DFORMAT)

        return self.get_rest_days_by_id(
            cr, uid, ids[0], week_start, context=context
        )

    def get_rest_days_by_id(self, cr, uid, Id, week_start, context=None):
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
        sched = self.browse(cr, uid, Id, context=context)
        if not sched.detail_ids:
            return res
        dtFirstDay = datetime.strptime(
            sched.detail_ids[0].date_start, OE_DTFORMAT)
        date_start = dtFirstDay.strftime(OE_DFORMAT) < week_start \
            and week_start + ' ' + dtFirstDay.strftime(
                '%H:%M:%S') or dtFirstDay.strftime(OE_DTFORMAT)
        dtNextWeek = datetime.strptime(
            date_start, OE_DTFORMAT) + relativedelta(weeks=+1)

        # Determine the appropriate rest day list to use
        #
        restday_ids = False
        dSchedStart = datetime.strptime(sched.date_start, OE_DFORMAT).date()
        dWeekStart = datetime.strptime(week_start, OE_DFORMAT).date()
        if dWeekStart == dSchedStart:
            restday_ids = sched.restday_ids1
        elif dWeekStart == dSchedStart + relativedelta(days=+7):
            restday_ids = sched.restday_ids2
        elif dWeekStart == dSchedStart + relativedelta(days=+14):
            restday_ids = sched.restday_ids3
        elif dWeekStart == dSchedStart + relativedelta(days=+21):
            restday_ids = sched.restday_ids4
        elif dWeekStart == dSchedStart + relativedelta(days=+28):
            restday_ids = sched.restday_ids5

        # If there is explicit rest day data use it, otherwise try to guess
        # based on which days are not scheduled.
        #
        res = []
        if restday_ids:
            res = [rd.sequence for rd in restday_ids]
        else:
            weekdays = ['0', '1', '2', '3', '4', '5', '6']
            scheddays = []
            for dtl in sched.detail_ids:
                # Make sure the date we're examining isn't in the previous week
                # or the next one
                if dtl.date_start < week_start or datetime.strptime(
                        dtl.date_start, OE_DTFORMAT) >= dtNextWeek:
                    continue
                if dtl.dayofweek not in scheddays:
                    scheddays.append(dtl.dayofweek)
            res = [int(d) for d in weekdays if d not in scheddays]
            # If there are no sched.details return nothing instead of *ALL* the
            # days in the week
            if len(res) == 7:
                res = []

        return res

    def onchange_employee_start_date(
            self, cr, uid, ids, employee_id, date_start, context=None):

        res = {
            'value': {
                'name': ''
            }
        }
        dStart = False
        edata = False
        if employee_id:
            edata = self.pool.get('hr.employee').read(
                cr, uid, employee_id, ['name', 'contract_id'], context=context)
        if date_start:
            dStart = datetime.strptime(date_start, '%Y-%m-%d').date()
            # The schedule must start on a Monday
            if dStart.weekday() != 0:
                res['value']['date_start'] = False
                res['value']['date_end'] = False
            else:
                dEnd = dStart + relativedelta(days=+6)
                res['value']['date_end'] = dEnd.strftime('%Y-%m-%d')

        if edata['name']:
            res['value']['name'] = edata['name']
            if dStart:
                res['value']['name'] = res['value']['name'] + ': ' + \
                    dStart.strftime('%Y-%m-%d') + ' Wk ' + str(
                        dStart.isocalendar()[1])

        if edata['contract_id']:
            cdata = self.pool.get('hr.contract').read(
                cr, uid, edata['contract_id'][0], ['schedule_template_id'],
                context=context
            )
            if cdata['schedule_template_id']:
                res['value']['template_id'] = cdata['schedule_template_id']

        return res

    def delete_details(self, cr, uid, sched_id, context=None):

        unlink_ids = []
        schedule = self.browse(cr, uid, sched_id, context=context)
        for detail in schedule.detail_ids:
            unlink_ids.append(detail.id)
        self.pool.get('hr.schedule.detail').unlink(
            cr, uid, unlink_ids, context=context)
        return

    def add_restdays(
            self, cr, uid, schedule, field_name, rest_days=None, context=None):

        _logger.warning('field: %s', field_name)
        _logger.warning('rest_days: %s', rest_days)
        restday_ids = []
        if rest_days is None:
            for rd in schedule.template_id.restday_ids:
                restday_ids.append(rd.id)
        else:
            restday_ids = self.pool.get('hr.schedule.weekday').search(
                cr, uid, [
                    ('sequence', 'in', rest_days)
                ], context=context)
        _logger.warning('restday_ids: %s', restday_ids)
        if len(restday_ids) > 0:
            self.write(cr, uid, schedule.id, {
                       field_name: [(6, 0, restday_ids)]}, context=context)

        return

    def create_details(self, cr, uid, sched_id, context=None):

        leave_obj = self.pool.get('hr.holidays')
        schedule = self.browse(cr, uid, sched_id, context=context)
        if schedule.template_id:
            leaves = []
            leave_ids = leave_obj.search(
                cr, uid, [('employee_id', '=', schedule.employee_id.id),
                          ('date_from', '<=', schedule.date_end),
                          ('date_to', '>=', schedule.date_start),
                          ('state', 'in', ['draft', 'validate', 'validate1'])],
                context=context)
            for lv in leave_obj.browse(cr, uid, leave_ids, context=context):
                utcdtFrom = utc.localize(
                    datetime.strptime(lv.date_from, OE_DTFORMAT), is_dst=False)
                utcdtTo = utc.localize(
                    datetime.strptime(lv.date_to, OE_DTFORMAT), is_dst=False)
                leaves.append((utcdtFrom, utcdtTo))

            user = self.pool.get('res.users').browse(
                cr, uid, uid, context=context)
            local_tz = timezone(user.tz)
            dCount = datetime.strptime(schedule.date_start, '%Y-%m-%d').date()
            dCountEnd = datetime.strptime(schedule.date_end, '%Y-%m-%d').date()
            dWeekStart = dCount
            dSchedStart = dCount
            while dCount <= dCountEnd:

                # Enter the rest day(s)
                #
                if dCount == dSchedStart:
                    self.add_restdays(
                        cr, uid, schedule, 'restday_ids1', context=context)
                elif dCount == dSchedStart + relativedelta(days=+7):
                    self.add_restdays(
                        cr, uid, schedule, 'restday_ids2', context=context)
                elif dCount == dSchedStart + relativedelta(days=+14):
                    self.add_restdays(
                        cr, uid, schedule, 'restday_ids3', context=context)
                elif dCount == dSchedStart + relativedelta(days=+21):
                    self.add_restdays(
                        cr, uid, schedule, 'restday_ids4', context=context)
                elif dCount == dSchedStart + relativedelta(days=+28):
                    self.add_restdays(
                        cr, uid, schedule, 'restday_ids5', context=context)

                prevutcdtStart = False
                prevDayofWeek = False
                for worktime in schedule.template_id.worktime_ids:

                    hour, sep, minute = worktime.hour_from.partition(':')
                    toHour, toSep, toMin = worktime.hour_to.partition(':')
                    if len(sep) == 0 or len(toSep) == 0:
                        raise models.except_orm(
                            _('Invalid Time Format'),
                            _('The time should be entered as HH:MM')
                        )

                    # TODO - Someone affected by DST should fix this
                    #
                    dtStart = datetime.strptime(dWeekStart.strftime(
                        '%Y-%m-%d') + ' ' + hour + ':' + minute + ':00',
                        '%Y-%m-%d %H:%M:%S')
                    locldtStart = local_tz.localize(dtStart, is_dst=False)
                    utcdtStart = locldtStart.astimezone(utc)
                    if worktime.dayofweek != 0:
                        utcdtStart = utcdtStart + \
                            relativedelta(days=+int(worktime.dayofweek))
                    dDay = utcdtStart.astimezone(local_tz).date()

                    # If this worktime is a continuation (i.e - after lunch)
                    # set the start time based on the difference from the
                    # previous record
                    #
                    if prevDayofWeek and prevDayofWeek == worktime.dayofweek:
                        prevHour = prevutcdtStart.strftime('%H')
                        prevMin = prevutcdtStart.strftime('%M')
                        curHour = utcdtStart.strftime('%H')
                        curMin = utcdtStart.strftime('%M')
                        delta_seconds = (
                            datetime.strptime(curHour + ':' + curMin, '%H:%M')
                            - datetime.strptime(prevHour + ':' + prevMin,
                                                '%H:%M')).seconds
                        utcdtStart = prevutcdtStart + \
                            timedelta(seconds=+delta_seconds)
                        dDay = prevutcdtStart.astimezone(local_tz).date()

                    delta_seconds = (datetime.strptime(toHour + ':' + toMin,
                                                       '%H:%M')
                                     - datetime.strptime(hour + ':' + minute,
                                                         '%H:%M')).seconds
                    utcdtEnd = utcdtStart + timedelta(seconds=+delta_seconds)

                    # Leave empty holes where there are leaves
                    #
                    _skip = False
                    for utcdtFrom, utcdtTo in leaves:
                        if utcdtFrom <= utcdtStart and utcdtTo >= utcdtEnd:
                            _skip = True
                            break
                        elif utcdtStart < utcdtFrom <= utcdtEnd:
                            if utcdtTo == utcdtEnd:
                                _skip = True
                            else:
                                utcdtEnd = utcdtFrom + timedelta(seconds=-1)
                            break
                        elif utcdtStart <= utcdtTo < utcdtEnd:
                            if utcdtTo == utcdtEnd:
                                _skip = True
                            else:
                                utcdtStart = utcdtTo + timedelta(seconds=+1)
                            break
                    if not _skip:
                        val = {
                            'name': schedule.name,
                            'dayofweek': worktime.dayofweek,
                            'day': dDay,
                            'date_start': utcdtStart.strftime(
                                '%Y-%m-%d %H:%M:%S'),
                            'date_end': utcdtEnd.strftime(
                                '%Y-%m-%d %H:%M:%S'),
                            'schedule_id': sched_id,
                        }
                        self.write(cr, uid, sched_id, {
                                   'detail_ids': [(0, 0, val)]},
                                   context=context)

                    prevDayofWeek = worktime.dayofweek
                    prevutcdtStart = utcdtStart

                dCount = dWeekStart + relativedelta(weeks=+1)
                dWeekStart = dCount
        return True

    def create(self, cr, uid, vals, context=None):

        my_id = super(hr_schedule, self).create(cr, uid, vals, context=context)

        self.create_details(cr, uid, my_id, context=context)

        return my_id

    def create_mass_schedule(self, cr, uid, context=None):
        """Creates tentative schedules for all employees based on the
        schedule template attached to their contract. Called from the
        scheduler.
        """

        sched_obj = self.pool.get('hr.schedule')
        ee_obj = self.pool.get('hr.employee')

        # Create a two-week schedule beginning from Monday of next week.
        #
        dt = datetime.today()
        days = 7 - dt.weekday()
        dt += relativedelta(days=+days)
        dStart = dt.date()
        dEnd = dStart + relativedelta(weeks=+2, days=-1)

        # Create schedules for each employee in each department
        #
        dept_ids = self.pool.get('hr.department').search(cr, uid, [],
                                                         context=context)
        for dept in self.pool.get('hr.department').browse(cr, uid, dept_ids,
                                                          context=context):
            ee_ids = ee_obj.search(cr, uid, [
                ('department_id', '=', dept.id),
            ], order="name", context=context)
            if len(ee_ids) == 0:
                continue

            for ee in ee_obj.browse(cr, uid, ee_ids, context=context):

                if (not ee.contract_id
                        or not ee.contract_id.schedule_template_id):
                    continue

                sched = {
                    'name': (ee.name + ': ' + dStart.strftime('%Y-%m-%d') +
                             ' Wk ' + str(dStart.isocalendar()[1])),
                    'employee_id': ee.id,
                    'template_id': ee.contract_id.schedule_template_id.id,
                    'date_start': dStart.strftime('%Y-%m-%d'),
                    'date_end': dEnd.strftime('%Y-%m-%d'),
                }
                sched_obj.create(cr, uid, sched, context=context)

    def deletable(self, cr, uid, sched_id, context=None):

        sched = self.browse(cr, uid, sched_id, context=context)
        if sched.state not in ['draft', 'unlocked']:
            return False
        for detail in sched.detail_ids:
            if detail.state not in ['draft', 'unlocked']:
                return False

        return True

    def unlink(self, cr, uid, ids, context=None):

        detail_obj = self.pool.get('hr.schedule.detail')

        if isinstance(ids, (int, long)):
            ids = [ids]

        schedule_ids = []
        for schedule in self.browse(cr, uid, ids, context=context):
            # Do not remove schedules that are not in draft or unlocked state
            if not self.deletable(cr, uid, schedule.id, context):
                continue

            # Delete the schedule details associated with this schedule
            #
            detail_ids = []
            [detail_ids.append(detail.id) for detail in schedule.detail_ids]
            if len(detail_ids) > 0:
                detail_obj.unlink(cr, uid, detail_ids, context=context)

            schedule_ids.append(schedule.id)

        return super(hr_schedule, self).unlink(
            cr, uid, schedule_ids, context=context)

    def _workflow_common(self, cr, uid, ids, signal, next_state, context=None):

        wkf = netsvc.LocalService('workflow')
        for sched in self.browse(cr, uid, ids, context=context):
            for detail in sched.detail_ids:
                wkf.trg_validate(
                    uid, 'hr.schedule.detail', detail.id, signal, cr)
            self.write(
                cr, uid, sched.id, {'state': next_state}, context=context)
        return True

    def workflow_validate(self, cr, uid, ids, context=None):
        return self._workflow_common(
            cr, uid, ids, 'signal_validate', 'validate', context=context)

    def details_locked(self, cr, uid, ids, context=None):

        for sched in self.browse(cr, uid, ids, context=context):
            for detail in sched.detail_ids:
                if detail.state != 'locked':
                    return False

        return True

    def workflow_lock(self, cr, uid, ids, context=None):
        """Lock the Schedule Record. Expects to be called by its
        schedule detail records as they are locked one by one.
        When the last one has been locked the schedule will also be
        locked.
        """

        all_locked = True
        for sched in self.browse(cr, uid, ids, context=context):
            if self.details_locked(cr, uid, [sched.id], context):
                self.write(cr, uid, sched.id, {
                           'state': 'locked'}, context=context)
            else:
                all_locked = False

        return all_locked

    def workflow_unlock(self, cr, uid, ids, context=None):
        """Unlock the Schedule Record. Expects to be called by its
        schedule detail records as they are unlocked one by one.
        When the first one has been unlocked the schedule will also be
        unlocked.
        """

        all_locked = True
        for sched in self.browse(cr, uid, ids, context=context):
            if not self.details_locked(cr, uid, [sched.id], context):
                self.write(
                    cr, uid, sched.id, {'state': 'unlocked'}, context=context)
            else:
                all_locked = False

        return all_locked is False
