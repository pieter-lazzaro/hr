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

from odoo import models, fields, api


def within_window(date_scheduled, date_punch_in, window, grace_period=0):
    difference = 0
    if date_scheduled >= date_punch_in:
        difference = abs((date_scheduled - date_punch_in).seconds) / 60
    else:
        difference = abs((date_punch_in - date_scheduled).seconds) / 60
    return difference < window and difference >= grace_period


class hr_schedule_alert_rule(models.Model):

    _name = 'hr.schedule.alert.rule'
    _description = 'Scheduling/Attendance Exception Rule'

    name = fields.Char(size=64, required=True)
    code = fields.Char(size=10, required=True)
    severity = fields.Selection((
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ), required=True, default='low')
    grace_period = fields.Integer(
        help='In the case of early or late rules, the amount of time '
        'before/after the scheduled time that the rule will trigger.'
    )
    window = fields.Integer('Window of Activation')
    active = fields.Boolean(default=True)

    @api.multi
    def check_unscheduled_attendance(self, sched_details, punches):
        self.ensure_one()
        res = {'schedule_details': [], 'punches': []}
        for punch in punches:
            
            is_match = False
            date_punch_in = fields.Datetime.from_string(punch.check_in)
            for detail in sched_details:
                date_scheduled = fields.Datetime.from_string(detail.date_start)
                if within_window(date_scheduled, date_punch_in, self.window):
                    is_match = True
                    break
            if not is_match:
                res['punches'].append((punch.check_in, punch.id))
        return res

    @api.multi
    def check_missed_attendance(self, sched_details, punches):
        self.ensure_one()
        res = {'schedule_details': [], 'punches': []}
        if len(sched_details) > len(punches):
            for detail in sched_details:
                is_match = False
                date_scheduled = fields.Datetime.from_string(detail.date_start)
                for punch in punches:
                    date_punch_in = fields.Datetime.from_string(punch.check_in)
                    if within_window(date_scheduled, date_punch_in, self.window):
                        is_match = True
                        break
                if not is_match:
                    res['schedule_details'].append(
                        (detail.date_start, detail.id))
        return res

    @api.multi
    def check_unscheduled_ot(self, sched_details, punches):
        self.ensure_one()
        res = {'schedule_details': [], 'punches': []}
        actual_hours = 0
        sched_hours = 0
        for detail in sched_details:
            date_start = fields.Datetime.from_string(detail.date_start)
            date_end = fields.Datetime.from_string(detail.date_end)
            sched_hours += float((date_end - date_start).seconds / 60) / 60.0

        for punch in punches:
            if punch.check_out:
                actual_hours += punch.worked_hours
                if actual_hours > sched_hours:
                    res['punches'].append((punch.check_in, punch.id))
        return res

    @api.multi
    def check_tardy(self, sched_details, punches):
        self.ensure_one()
        res = {'punches': []}
        for detail in sched_details:
            is_match = False
            date_scheduled = fields.Datetime.from_string(detail.date_start)
            for punch in punches:
                date_punch_in = fields.Datetime.from_string(punch.check_in)
                difference = 0
                if date_punch_in > date_scheduled:
                    difference = (date_punch_in - date_scheduled).seconds / 60
                
                if self.window > difference > self.grace_period:
                    is_match = True
                    break
            if is_match:
                res['punches'].append((punch.check_in, punch.id))
        return res

    @api.multi
    def check_leave_early(self, sched_details, punches):
        self.ensure_one()
        res = {'schedule_details': [], 'punches': []}
        for detail in sched_details:
            
            is_match = False
            date_scheduled = fields.Datetime.from_string(detail.date_end)
            
            for punch in punches:
                if not punch.check_out:
                    continue
                
                date_punch_out = fields.Datetime.from_string(punch.check_out)
                print(date_scheduled, date_punch_out)
                difference = 0
                if date_punch_out < date_scheduled:
                    difference = (date_scheduled - date_punch_out).seconds / 60
                if self.window > difference > self.grace_period:
                    is_match = True
                    break
            if is_match:
                res['punches'].append((punch.check_in, punch.id))
        return res

    @api.multi
    def check_arrive_early(self, sched_details, punches):
        self.ensure_one()
        res = {'schedule_details': [], 'punches': []}
        for detail in sched_details:
            is_match = False
            date_scheduled = fields.Datetime.from_string(detail.date_start)
            for punch in punches:
                date_punch_in = fields.Datetime.from_string(punch.check_in)
                difference = 0
                if date_punch_in < date_scheduled:
                    difference = (date_scheduled - date_punch_in).seconds / 60
                if self.window > difference > self.grace_period:
                    is_match = True
                    break
            if is_match:
                res['punches'].append((punch.check_in, punch.id))
        return res

    @api.multi
    def check_leave_late(self, sched_details, punches):
        self.ensure_one()
        res = {'schedule_details': [], 'punches': []}
        for detail in sched_details:
            is_match = False
            date_scheduled = fields.Datetime.from_string(detail.date_end)
            for punch in punches:
                if not punch.check_out:
                    continue

                date_punch_out = fields.Datetime.from_string(punch.check_out)
                difference = 0
                if date_punch_out > date_scheduled:
                    difference = (date_punch_out - date_scheduled).seconds / 60
                if self.window > difference > self.grace_period:
                    is_match = True
                    break
            if is_match:
                res['punches'].append((punch.check_in, punch.id))
        return res

    @api.multi
    def check_overlap(self, sched_details, punches):
        self.ensure_one()
        res = {'schedule_details': [], 'punches': []}
        leave_obj = self.env['hr.holidays']
        for punch in punches:
            date_punch_in = fields.Datetime.from_string(punch.check_in)
            date_punch_out = fields.Datetime.from_string(punch.check_out)
            
            leave_ids = leave_obj.search([('employee_id', '=', punch.employee_id.id),
                                            ('type', '=', 'remove'),
                                            ('date_from', '<=', punch.check_out),
                                            ('date_to', '>=', punch.check_in),
                                            ('state', 'in', ['validate', 'validate1'])])
            if len(leave_ids) > 0:
                res['punches'].append((punch.name_get(), punch.id))
                break

        return res

    @api.multi
    def check_rule(self, sched_details, punches):
        """Identify if the schedule detail or attendance records
        trigger any rule. If they do return the datetime and id of the
        record that triggered it in one of the appropriate lists.
        All schedule detail and attendance records are expected to be
        in sorted order according to datetime.
        """
        self.ensure_one()

        if self.code == 'MISSPUNCH':
            # Not used because attendance rules now enforce correct order
            pass
        elif self.code == 'UNSCHEDATT':
            return self.check_unscheduled_attendance(sched_details, punches)
        elif self.code == 'MISSATT':
            return self.check_missed_attendance(sched_details, punches)
        # elif self.code == 'UNSCHEDOT':
        #     return self.check_unscheduled_ot(sched_details, punches)
        elif self.code == 'TARDY':
            return self.check_tardy(sched_details, punches)
        elif self.code == 'OUTEARLY':
            return self.check_leave_early(sched_details, punches)
        elif self.code == 'INEARLY':
            return self.check_arrive_early(sched_details, punches)
        elif self.code == 'OUTLATE':
            return self.check_leave_late(sched_details, punches)
        elif self.code == 'OVRLP':
            return self.check_overlap(sched_details, punches)

        return {'schedule_details': [], 'punches': []}
