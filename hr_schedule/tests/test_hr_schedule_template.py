##############################################################################
#
#    Copyright (C) 2014 Savoir-faire Linux. All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by
#    the Free Software Foundation, either version 3 of the License, or
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
##############################################################################

from datetime import date

from odoo.tests import common
from odoo import fields
from odoo.exceptions import UserError


class test_hr_schedule_template(common.TransactionCase):
    def setUp(self):
        super(test_hr_schedule_template, self).setUp()
        self.template_model = self.env['hr.schedule.template']

    def test_get_rest_days_when_defined(self):
        """
        Test that templates compute the right rest days when explicitly defined
        """

        template = self.template_model.create({
            'name': 'test template',
        })