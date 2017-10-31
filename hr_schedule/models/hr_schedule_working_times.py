
from odoo import models, fields
from odoo.tools.translate import _

from .week_days import DAYOFWEEK_SELECTION

class hr_schedule_working_times(models.Model):

    _name = "hr.schedule.template.worktime"
    _description = "Work Detail"

    name = fields.Char(
        "Name",
        size=64,
        required=True,
    )
    dayofweek = fields.Selection(
        DAYOFWEEK_SELECTION,
        'Day of Week',
        required=True,
        index=True,
    )
    hour_from = fields.Char(
        'Work From',
        size=5,
        required=True,
        index=True,
    )
    hour_to = fields.Char(
        "Work To",
        size=5,
        required=True,
    )
    template_id = fields.Many2one(
        'hr.schedule.template',
        'Schedule Template',
        required=True,
    )

    _order = 'dayofweek, name'

    def _rec_message(self, cr, uid, ids, context=None):
        return _('Duplicate Records!')

    _sql_constraints = [
        ('unique_template_day_from',
         'UNIQUE(template_id, dayofweek, hour_from)', _rec_message),
        ('unique_template_day_to',
         'UNIQUE(template_id, dayofweek, hour_to)', _rec_message),
    ]

    _defaults = {
        'dayofweek': '0'
    }

