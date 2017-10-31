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

from pytz import timezone, utc

from odoo import models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

class hr_term(models.Model):

    _inherit = 'hr.employee.termination'

    def create(self, cr, uid, vals, context=None):

        res = super(hr_term, self).create(cr, uid, vals, context=context)

        det_obj = self.pool.get('hr.schedule.detail')
        term = self.browse(cr, uid, res, context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        if user and user.tz:
            local_tz = timezone(user.tz)
        else:
            local_tz = timezone('Africa/Addis_Ababa')
        dt = datetime.strptime(term.name + ' 00:00:00', OE_DTFORMAT)
        utcdt = (local_tz.localize(dt, is_dst=False)).astimezone(utc)
        det_ids = det_obj.search(
            cr, uid, [('schedule_id.employee_id', '=', term.employee_id.id),
                      ('date_start', '>=', utcdt.strftime(OE_DTFORMAT))],
            order='date_start', context=context)
        det_obj.unlink(cr, uid, det_ids, context=context)

        return res

    def _restore_schedule(self, cr, uid, ids, context=None):

        if isinstance(ids, (int, long)):
            ids = [ids]

        sched_obj = self.pool.get('hr.schedule')
        for term in self.browse(cr, uid, ids, context=context):
            d = datetime.strptime(term.name, OE_DFORMAT).date()
            sched_ids = sched_obj.search(
                cr, uid, [('employee_id', '=', term.employee_id.id),
                          ('date_start', '<=', d.strftime(
                              OE_DFORMAT)),
                          ('date_end', '>=', d.strftime(OE_DFORMAT))])

            # Re-create affected schedules from scratch
            for sched_id in sched_ids:
                sched_obj.delete_details(cr, uid, sched_id, context=context)
                sched_obj.create_details(cr, uid, sched_id, context=context)

        return

    def state_cancel(self, cr, uid, ids, context=None):

        self._restore_schedule(cr, uid, ids, context=context)
        res = super(hr_term, self).state_cancel(cr, uid, ids, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):

        self._restore_schedule(cr, uid, ids, context=context)
        res = super(hr_term, self).unlink(cr, uid, ids, context=context)
        return res
