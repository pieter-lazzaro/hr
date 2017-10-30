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


class test_hr_init_wage(common.TransactionCase):
    def setUp(self):
        super(test_hr_init_wage, self).setUp()
        self.contract_init_model = self.env['hr.contract.init']
        self.wage_init_model = self.env['hr.contract.init.wage']

        # Create settings and wage
        self.init = self.contract_init_model.create({
            'name': 'test settings',
            'date': fields.Date.today(),
        })

        self.wage = self.wage_init_model.create({
            'contract_init_id': self.init.id,
            'starting_wage': 10000,
        })


    def test_cannot_delete_approved(self):
        """
        Test that a wage setting cannot be deleted if the initial setting is approved
        """
        
        self.init.action_approve()

        with self.assertRaises(UserError):
            self.wage.unlink()

    def test_cannot_delete_declined(self):
        """
        Test that initial settings cannot be deleted if declined
        """
        
        self.init.action_decline()

        with self.assertRaises(UserError):
            self.wage.unlink()
    
    def test_can_delete_draft(self):
        """
        Test that initial settings can be deleted if a draft
        """
     
        # Try and delete, should not raise anything
        self.wage.unlink()