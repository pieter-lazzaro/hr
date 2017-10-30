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
        
        # # Create a employee
        # self.employee_id = self.employee_model.create({'name': 'Employee 1'})

        # # Create two employee categories
        # self.categ_id = self.employee_categ_model.create(
        #     {'name': 'Category 1'})
        # self.categ_2_id = self.employee_categ_model.create(
        #     {'name': 'Category 2'})

        # # Create two jobs
        # self.job_id = self.job_model.create(
        #     {'name': 'Job 1',
        #      'category_ids': [(6, 0, [self.categ_id.id])]})

        # self.job_2_id = self.job_model.create(
        #     {'name': 'Job 2',
        #      'category_ids': [(6, 0, [self.categ_2_id.id])]})

        # # Create one contract
        # self.contract_id = self.contract_model.create(
        #     {'name': 'Contract 1',
        #      'employee_id': self.employee_id.id,
        #      'wage': 50000})

        # Remove all initial settings
        inits = self.contract_init_model.search([])
        inits.action_draft()
        inits.unlink()

    def test_get_latest_initial_values_returns_none_when_not_set(self):
        """
        Test that get_latest_initial_values returns None if there aren't any set
        """

        initial_values = self.contract_model.get_latest_initial_values()

        self.assertIsNone(initial_values)

    def test_get_latest_initial_values_return_for_future(self):
        """
        Test that get_latest_initial_values returns None if all settings are not effective
        until a future date
        """

        self.contract_init_model.create({
            'name': 'future settings',
            'date': fields.Date.to_string(date.today() + timedelta(days=1))
        })

        initial_values = self.contract_model.get_latest_initial_values()

        self.assertIsNone(initial_values)

    def test_get_latest_initial_values_return(self):
        """
        Test that get_latest_initial_values returns the correct initial values
        """

        initial = self.contract_init_model.create({
            'name': 'today settings',
            'date': fields.Date.today()
        })

        initial.action_approve()

        latest = self.contract_model.get_latest_initial_values()

        self.assertEqual(initial, latest)

    def test_get_latest_initial_values_return_multiple(self):
        """
        Test that get_latest_initial_values returns the correct initial values
        when there are multiple
        """

        today_settings = self.contract_init_model.create({
            'name': 'today settings',
            'date': fields.Date.today()
        })

        yesterday_settings = self.contract_init_model.create({
            'name': 'yesterday settings',
            'date': fields.Date.to_string(date.today() - timedelta(days=1))
        })

        future_settings = self.contract_init_model.create({
            'name': 'future settings',
            'date': fields.Date.to_string(date.today() + timedelta(days=1))
        })

        today_settings.action_approve()
        yesterday_settings.action_approve()
        future_settings.action_approve()

        latest = self.contract_model.get_latest_initial_values()

        self.assertEqual(today_settings, latest)

    def test_uses_latest_wage_as_default(self):
        """
        Test contracts use the default wage
        """

        initial = self.contract_init_model.create({
            'name': 'today settings',
            'date': fields.Date.today()
        })

        wage = self.wage_init_model.create({
            'contract_init_id': initial.id,
            'starting_wage': 10000,
            'is_default': True
        })

        initial.action_approve()

        default_wage = self.contract_model._default_get_wage()

        self.assertEqual(wage.starting_wage, default_wage)
    
    def test_uses_latest_wage_for_job_as_default(self):
        """
        Test contracts use the wage for a job if it is set
        """

        initial = self.contract_init_model.create({
            'name': 'today settings',
            'date': fields.Date.today()
        })

        job = self.job_model.create({
            'name': 'test job'
        })

        wage = self.wage_init_model.create({
            'contract_init_id': initial.id,
            'starting_wage': 10000,
            'job_id': job.id
        })

        initial.action_approve()

        default_wage = self.contract_model._default_get_wage(job.id)

        self.assertEqual(wage.starting_wage, default_wage)
    
    def test_uses_latest_wage_for_job_category_as_default(self):
        """
        Test contracts use the wage for a job if it is set
        """

        categ_id = self.employee_categ_model.create({
            'name': 'Category 1'
        })

        job = self.job_model.create({
            'name': 'test job',
            'category_ids': [(6, 0, [categ_id.id])]
        })

        initial = self.contract_init_model.create({
            'name': 'today settings',
            'date': fields.Date.today()
        })

        wage = self.wage_init_model.create({
            'contract_init_id': initial.id,
            'starting_wage': 10000,
            'category_ids': [(6, 0, [categ_id.id])]
        })

        initial.action_approve()

        default_wage = self.contract_model._default_get_wage(job.id)

        self.assertEqual(wage.starting_wage, default_wage)

    def test_uses_latest_salary_structure_as_default(self):
        """
        Test contracts use the default wage
        """

        struct = self.payrol_structure_model.create({
            'name': 'test structure',
            'code': 'TEST'
        })

        initial = self.contract_init_model.create({
            'name': 'today settings',
            'date': fields.Date.today(),
            'struct_id': struct.id
        })

        initial.action_approve()

        default_struct_id = self.contract_model._default_get_struct()

        self.assertEqual(struct.id, default_struct_id)

    def test_uses_latest_trial_period_as_default(self):
        """
        Test contracts use the default wage
        """

        initial = self.contract_init_model.create({
            'name': 'today settings',
            'date': fields.Date.today(),
            'trial_period': 7
        })

        initial.action_approve()

        default_trial_end = self.contract_model._default_get_trial_date_end()

        trial_end = fields.Date.to_string(date.today() + timedelta(days=7))

        self.assertEqual(trial_end, default_trial_end)
