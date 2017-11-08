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

    @api.model
    def create(self, vals):

        res = super(hr_attendance, self).create(vals)

        res.compute_alerts()

        return res

    @api.multi
    def unlink(self):

        # Remove alerts directly attached to the attendances
        #
        self._remove_direct_alerts()

        res = super(hr_attendance, self).unlink()

        return res

    @api.multi
    def write(self, vals):

        res = super(hr_attendance, self).write(vals)

        if 'check_in' in vals or 'check_out' in vals:
            self._remove_direct_alerts()
            self.compute_alerts()

        return res

    @api.multi
    def _remove_direct_alerts(self):
        """Remove alerts directly attached to the attendance.
        """

        for attendance in self:
            attendance.alert_ids.unlink()

    @api.multi
    def compute_alerts(self):
        alert_obj = self.env['hr.schedule.alert']

        for attendance in self:
            alert_obj.compute_alerts_for_attendance(attendance)
