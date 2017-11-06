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


from odoo import models, api, fields


def is_shift_missed(shift, leave):
    return leave.date_from <= shift.date_start and leave.date_to >= shift.date_end


class HRHolidays(models.Model):

    _inherit = 'hr.holidays'

    @api.multi
    def action_validate(self):

        res = super(HRHolidays, self).action_validate()

        det_obj = self.env['hr.schedule.detail']
        for leave in self:

            if leave.type != 'remove':
                continue

            scheduled_shifts = det_obj.search(
                [('employee_id', '=', leave.employee_id.id),
                 ('date_start', '<=', leave.date_to),
                 ('date_end', '>=', leave.date_from)],
                order='date_start',
            )

            missed_shifts = scheduled_shifts.filtered(
                lambda shift: is_shift_missed(shift, leave))

            missed_shifts.unlink()

            for shift in scheduled_shifts - missed_shifts:
                # Change the shifts to end when the leave starts
                if shift.date_start < leave.date_from < shift.date_end:
                    shift.write({
                        'date_end': leave.date_from
                    })

                # Change the shifts to start when the leave eands
                elif shift.date_end > leave.date_to >= shift.date_start:
                    shift.write({
                        'date_start': leave.date_to
                    })
        return res

    @api.multi
    def action_refuse(self):

        res = super(HRHolidays, self).action_refuse()

        sched_obj = self.env['hr.schedule']
        for leave in self:
            if leave.type != 'remove':
                continue

            datetime_leave_from = fields.Datetime.fromString(
                leave.date_from).date()
            datetime_leave_to = fields.Datetime.fromString(
                leave.date_to).date()
            affected_schedules = sched_obj.search([
                ('employee_id', '=', leave.employee_id.id),
                ('date_start', '<=', fields.Date.to_string(datetime_leave_to)),
                ('date_end', '>=', fields.Date.to_string(datetime_leave_from))
            ])

            # Re-create affected schedules from scratch
            affected_schedules.delete_details()
            affected_schedules.create_details()

        return res
