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

from datetime import date, timedelta

from odoo.tests import common
from odoo import fields
from odoo.exceptions import UserError


class test_hr_contract(common.TransactionCase):
    def setUp(self):
        super(test_hr_contract, self).setUp()
        self.contract_init_model = self.env['hr.contract.init']
        self.contract_model = self.env['hr.contract']
        self.wage_init_model = self.env['hr.contract.init.wage']
        self.payrol_structure_model = self.env['hr.payroll.structure']

        self.employee_model = self.env['hr.employee']
        self.employee_categ_model = self.env['hr.employee.category']
        self.job_model = self.env['hr.job']

        self.employee = self.employee_model.create({'name': 'test employee'})

    def test_trial_period(self):
        """
        Test is_trial_active when trial is still going
        """

        contract = self.contract_model.create({
            'name': 'test',
            'trial_date_end': fields.Date.to_string(date.today() + timedelta(days=1)),
            'employee_id': self.employee.id,
            'wage': 0
        })

        self.assertTrue(contract.is_trial_active())

    def test_trial_period_false(self):
        """
        Test is_trial_active false when trial period over
        """

        contract = self.contract_model.create({
            'name': 'test',
            'trial_date_end': fields.Date.to_string(date.today() - timedelta(days=1)),
            'employee_id': self.employee.id,
            'wage': 0
        })

        self.assertFalse(contract.is_trial_active())

    def test_ending_contracts(self):
        """
        Test ending contracts only toggles contracts ending in less than 30 days
        """
        contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'date_end': fields.Date.to_string(date.today() + timedelta(days=10)),
            'state': 'open'
        })

        contract2 = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'date_end': fields.Date.to_string(date.today() + timedelta(days=40)),
            'state': 'open'
        })

        self.contract_model.try_ending_contracts()

        self.assertEqual('contract_ending', contract.state)
        self.assertEqual('open', contract2.state)

    def test_ended_contracts(self):
        """
        Test ended contracts only toggles contracts that have ended
        """
        contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'date_start': fields.Date.to_string(date.today() - timedelta(days=20)),
            'date_end': fields.Date.to_string(date.today() - timedelta(days=1)),
            'state': 'open'
        })

        contract2 = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'date_end': fields.Date.to_string(date.today() + timedelta(days=40)),
            'state': 'open'
        })

        self.contract_model.try_contract_completed()

        self.assertEqual('pending_done', contract.state)
        self.assertEqual('open', contract2.state)

    def test_ending_trials(self):
        """
        Test ending trials only toggles contracts with trials ending in less than 10 days
        """
        contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'trial_date_end': fields.Date.to_string(date.today() + timedelta(days=5)),
            'state': 'trial'
        })

        contract2 = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'trial_date_end': fields.Date.to_string(date.today() + timedelta(days=40)),
            'state': 'trial'
        })

        self.contract_model.try_ending_trial()

        self.assertEqual('trial_ending', contract.state)
        self.assertEqual('trial', contract2.state)

    def test_ended_trials(self):
        """
        Test ended trials only toggles contracts with trials that ended in more than 5 days ago
        """
        contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'trial_date_end': fields.Date.to_string(date.today() - timedelta(days=6)),
            'state': 'trial_ending'
        })

        contract2 = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'trial_date_end': fields.Date.to_string(date.today()),
            'state': 'trial'
        })

        self.contract_model.try_open()

        self.assertEqual('open', contract.state)
        self.assertEqual('trial', contract2.state)

    def test_confirm_with_trial(self):
        """
        Test confirm switches state to trial if needed
        """
        contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
            'trial_date_end': fields.Date.to_string(date.today() + timedelta(days=5)),
        })

        contract.action_confirm()

        self.assertEqual('trial', contract.state)

    def test_confirm_without_trial(self):
        """
        Test confirm switches state to open when there isn't a trial
        """
        contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'wage': 0,
        })

        contract.action_confirm()

        self.assertEqual('open', contract.state)
    
    def test_done_with_end_date(self):
        """ Test correct values are written to contract when it is done and has an end date """
        job = self.job_model.create({'name': 'test job'})

        end_date = fields.Date.to_string(date.today() + timedelta(days=1))
        contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'job_id': job.id,
            'wage': 0,
            'date_end': end_date,
        })

        contract.action_done()

        self.assertEqual('done', contract.state)
        self.assertEqual(end_date, contract.date_end)
        self.assertEqual(job.id, contract.end_job_id.id)

    def test_done_without_end_date(self):
        """ 
        Test correct values are written to contract when it is done and has doesn't 
        have an end date
        """
        job = self.job_model.create({'name': 'test job'})

        contract = self.contract_model.create({
            'name': 'test',
            'employee_id': self.employee.id,
            'job_id': job.id,
            'wage': 0,
        })

        contract.action_done()

        self.assertEqual('done', contract.state)
        self.assertEqual(fields.Date.today(), contract.date_end)
        self.assertEqual(job.id, contract.end_job_id.id)
