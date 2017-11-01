
from odoo import models, fields
from odoo.tools.translate import _

from .week_days import DAYOFWEEK_SELECTION


class hr_schedule_working_times(models.Model):

    _name = "hr.schedule.template.worktime"
    _description = "Work Detail"

    name = fields.Char(size=64, required=True)
    week = fields.Integer(required=True, default=1)
    dayofweek = fields.Selection(
        DAYOFWEEK_SELECTION,
        'Day of Week',
        required=True,
        index=True,
        default='0'
    )
    hour_from = fields.Float('Work From', required=True, index=True)
    hour_to = fields.Float("Work To", required=True)
    template_id = fields.Many2one(
        'hr.schedule.template', 'Schedule Template', required=True)

    _order = 'week, dayofweek, hour_from'

    def _rec_message(self):
        return _('Duplicate Records!')

    _sql_constraints = [
        ('unique_template_day_from',
         'UNIQUE(template_id, week, dayofweek, hour_from)', _rec_message),
        ('unique_template_day_to',
         'UNIQUE(template_id, week, dayofweek, hour_to)', _rec_message),
    ]
