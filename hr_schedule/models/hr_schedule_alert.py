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

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from odoo.tools.translate import _


class HrScheduleAlert(models.Model):

    _name = 'hr.schedule.alert'
    _description = 'Attendance Exception'
    _inherit = ['mail.thread']

    @api.multi
    @api.depends('punch_id', 'sched_detail_id')
    def _get_employee_id(self):

        for alert in self:
            if alert.punch_id:
                alert.employee_id = alert.punch_id.employee_id.id
            elif alert.sched_detail_id:
                alert.employee_id = alert.sched_detail_id.schedule_id.employee_id.id
            else:
                alert.employee_id = False

    name = fields.Datetime(
        'Date and Time',
        required=True,
        readonly=True,
    )
    rule_id = fields.Many2one(
        'hr.schedule.alert.rule',
        'Alert Rule',
        required=True,
        readonly=True,
    )
    punch_id = fields.Many2one(
        'hr.attendance',
        'Triggering Punch',
        readonly=True,
    )
    sched_detail_id = fields.Many2one(
        'hr.schedule.detail',
        'Shift',
        readonly=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        compute="_get_employee_id",
        method=True,
        store=True,
        string='Employee',
        readonly=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True)
    severity = fields.Selection(
        related='rule_id.severity',
        string='Severity',
        store=True,
        readonly=True)
    state = fields.Selection(
        [
            ('unresolved', 'Unresolved'),
            ('resolved', 'Resolved'),
        ],
        'State',
        readonly=True,
        default='unresolved'
    )

    _track = {
        'state': {
            'hr_schedule.mt_alert_resolved': (
                lambda self, r, u, obj, ctx=None: obj['state'] == 'resolved'
            ),
            'hr_schedule.mt_alert_unresolved': (
                lambda self, r, u, obj, ctx=None: obj['state'] == 'unresolved'
            ),
        },
    }

    def check_for_alerts(self):
        """Check the schedule detail and attendance records for
        yesterday against the scheduling/attendance alert rules.
        If any rules match create a record in the database.
        """

        dept_obj = self.env['hr.department']
        detail_obj = self.env['hr.schedule.detail']
        attendance_obj = self.env['hr.attendance']
        rule_obj = self.env['hr.schedule.alert.rule']

        # TODO - Someone who cares about DST should fix ths
        #
        user_tz = self.env.user.tz
        dtToday = datetime.strptime(
            datetime.now().strftime('%Y-%m-%d') + ' 00:00:00',
            '%Y-%m-%d %H:%M:%S')
        lcldtToday = timezone(user_tz and user_tz or 'UTC').localize(
            dtToday, is_dst=False)
        utcdtToday = lcldtToday.astimezone(utc)
        utcdtYesterday = utcdtToday + relativedelta(days=-1)
        strToday = utcdtToday.strftime('%Y-%m-%d %H:%M:%S')
        strYesterday = utcdtYesterday.strftime('%Y-%m-%d %H:%M:%S')

        dept_ids = dept_obj.search([])
        for dept in dept_ids:
            for employee in dept.member_ids:

                # Get schedule and attendance records for the employee for the
                # day
                #
                sched_detail_ids = detail_obj.search([
                    ('schedule_id.employee_id', '=', employee.id),
                    '&',
                    ('date_start', '>=', strYesterday),
                    ('date_start', '<', strToday),
                ],
                    order='date_start'
                )
                attendance_ids = attendance_obj.search([
                    ('employee_id', '=', employee.id),
                    '&',
                    ('name', '>=', strYesterday),
                    ('name', '<', strToday),
                ],
                    order='name'
                )

                # Run the schedule and attendance records against each active
                # rule, and create alerts for each result returned.
                #
                rule_ids = rule_obj.search([('active', '=', True)])
                for rule in rule_ids:
                    res = rule_obj.check_rule(
                        sched_detail_ids,
                        attendance_ids
                    )

                    for strdt, attendance_id in res['punches']:
                        # skip if it has already been triggered
                        ids = self.search([
                            ('punch_id', '=', attendance_id),
                            ('rule_id', '=', rule.id),
                            ('name', '=', strdt),
                        ])
                        if len(ids) > 0:
                            continue

                        self.create({
                            'name': strdt,
                            'rule_id': rule.id,
                            'punch_id': attendance_id,
                        })

                    for strdt, detail_id in res['schedule_details']:
                        # skip if it has already been triggered
                        ids = self.search([
                            ('sched_detail_id', '=', detail_id),
                            ('rule_id', '=', rule.id),
                            ('name', '=', strdt),
                        ])
                        if len(ids) > 0:
                            continue

                        self.create({
                            'name': strdt,
                            'rule_id': rule.id,
                            'sched_detail_id': detail_id,
                        })

    @api.model
    def compute_alerts(self, shifts, attendances):
        alert_rule_model = self.env['hr.schedule.alert.rule']
        rules = alert_rule_model.search([('active', '=', True)])
        for rule in rules:
            res = rule.check_rule(
                shifts,
                attendances
            )

            if 'punches' in res:
                for strdt, attendance_id in res['punches']:
                    # skip if it has already been triggered
                    ids = self.search([('punch_id', '=', attendance_id),
                                       ('rule_id', '=', rule.id),
                                       ('name', '=', strdt),
                                       ],)
                    if len(ids) > 0:
                        continue

                    self.create({'name': strdt,
                                 'rule_id': rule.id,
                                 'punch_id': attendance_id})

            if 'schedule_details' in res:
                for strdt, detail_id in res['schedule_details']:
                    # skip if it has already been triggered
                    ids = self.search([('sched_detail_id', '=', detail_id),
                                       ('rule_id', '=', rule.id),
                                       ('name', '=', strdt),
                                       ])
                    if len(ids) > 0:
                        continue

                    self.create({'name': strdt,
                                 'rule_id': rule.id,
                                 'sched_detail_id': detail_id})

    @api.model
    def compute_alerts_for_attendance(self, attendance):
        """ Compute the alerts that are triggered by an attendance """
        shift_model = self.env['hr.schedule.detail']

        # TODO use alert rules to set this
        max_window = 300

        date_start = fields.Datetime.from_string(
            attendance.check_in) - relativedelta(minutes=max_window)
        date_end = fields.Datetime.from_string(
            attendance.check_in) + relativedelta(minutes=max_window)

        shifts = shift_model.search([('schedule_id.employee_id', '=', attendance.employee_id.id),
                                     '&',
                                     ('date_start', '>=',
                                      fields.Datetime.to_string(date_start)),
                                     ('date_start', '<',
                                      fields.Datetime.to_string(date_end)),
                                     ],
                                    order='date_start')

        self.compute_alerts(shifts, [attendance])

    @api.model
    def compute_alerts_for_shift(self, shift):
        """ Compute the alerts that are triggered by an shift """
        attendance_model = self.env['hr.attendance']

        # TODO use alert rules to set this
        max_window = 300

        date_start = fields.Datetime.from_string(
            shift.date_start) - relativedelta(minutes=max_window)
        date_end = fields.Datetime.from_string(
            shift.date_start) + relativedelta(minutes=max_window)

        attendances = attendance_model.search([('employee_id', '=', shift.employee_id.id),
                                               '&',
                                               ('check_in', '>=',
                                                fields.Datetime.to_string(date_start)),
                                               ('check_in', '<',
                                                fields.Datetime.to_string(date_end)),
                                               ],
                                              order='check_in')

        self.compute_alerts([shift], attendances)

    @api.model
    def compute_alerts_by_employee(self, employee, date_start, date_end=None):
        """ Compute alerts for employee on specified range."""

        detail_obj = self.env['hr.schedule.detail']
        atnd_obj = self.env['hr.attendance']
        rule_obj = self.env['hr.schedule.alert.rule']

        if date_end is None:
            date_end = date_start + relativedelta(days=+1)

        # Get schedule and attendance records for the employee for the day
        #
        shifts = detail_obj.search([('schedule_id.employee_id', '=', employee.id),
                                    '&',
                                    ('date_start', '>=',
                                     fields.Datetime.to_string(date_start)),
                                    ('date_start', '<',
                                     fields.Datetime.to_string(date_end)),
                                    ],
                                   order='date_start')

        attendances = atnd_obj.search([('employee_id', '=', employee.id),
                                       '&',
                                       ('check_in', '>=',
                                        fields.Datetime.to_string(date_start)),
                                       ('check_in', '<',
                                        fields.Datetime.to_string(date_end)),
                                       ],
                                      order='check_in')

        # Run the schedule and attendance records against each active rule, and
        # create alerts for each result returned.
        #
        self.compute_alerts(shifts, attendances)
