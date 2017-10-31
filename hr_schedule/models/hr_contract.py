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

from odoo import models, fields


class hr_contract(models.Model):

    _name = 'hr.contract'
    _inherit = 'hr.contract'

    schedule_template_id = fields.Many2one(
        'hr.schedule.template',
        'Working Schedule Template',
        required=True,
    )

    def _get_sched_template(self, cr, uid, context=None):

        res = False
        init = self.get_latest_initial_values(cr, uid, context=context)
        if init is not None and init.sched_template_id:
            res = init.sched_template_id.id
        return res

    _defaults = {
        'schedule_template_id': _get_sched_template,
    }

