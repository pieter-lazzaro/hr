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

from odoo import models, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT


class hr_holidays(models.Model):

    _inherit = 'hr.holidays'

    @api.multi
    def holidays_validate(self):

        res = super(hr_holidays, self).holidays_validate()

        unlink_ids = []
        det_obj = self.env['hr.schedule.detail']
        for leave in self:
            if leave.type != 'remove':
                continue

            det_ids = det_obj.search([(
                'schedule_id.employee_id', '=', leave.employee_id.id),
                ('date_start', '<=', leave.date_to),
                ('date_end', '>=', leave.date_from)],
                order='date_start')

            for detail in det_ids:

                # Remove schedule details completely covered by leave
                if (leave.date_from <= detail.date_start
                        and leave.date_to >= detail.date_end
                        and detail.id not in unlink_ids):
                    unlink_ids.append(detail.id)

                # Partial day on first day of leave
                elif detail.date_start < leave.date_from <= detail.date_end:
                    dtLv = datetime.strptime(leave.date_from, OE_DTFORMAT)
                    if leave.date_from == detail.date_end:
                        if detail.id not in unlink_ids:
                            unlink_ids.append(detail.id)
                        else:
                            dtEnd = dtLv + timedelta(seconds=-1)
                            detail.write({
                                'date_end': dtEnd.strftime(OE_DTFORMAT)
                            })

                # Partial day on last day of leave
                elif detail.date_end > leave.date_to >= detail.date_start:
                    dtLv = datetime.strptime(leave.date_to, OE_DTFORMAT)
                    if leave.date_to != detail.date_start:
                        dtStart = dtLv + timedelta(seconds=+1)
                        detail.write(
                            {'date_start': dtStart.strftime(OE_DTFORMAT)})

        det_obj.browse(unlink_ids).unlink()

        return res

    @api.multi
    def holidays_refuse(self):

        res = super(hr_holidays, self).holidays_refuse()

        sched_obj = self.env['hr.schedule']
        for leave in self:
            if leave.type != 'remove':
                continue

            dLvFrom = datetime.strptime(leave.date_from, OE_DTFORMAT).date()
            dLvTo = datetime.strptime(leave.date_to, OE_DTFORMAT).date()
            sched_ids = sched_obj.search([('employee_id', '=', leave.employee_id.id),
                                          ('date_start', '<=', dLvTo.strftime(
                                              OE_DFORMAT)),
                                          ('date_end', '>=', dLvFrom.strftime(OE_DFORMAT))])

            # Re-create affected schedules from scratch
            sched_ids.delete_details()
            sched_ids.create_details()

        return res
