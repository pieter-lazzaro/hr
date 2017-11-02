
from odoo import models, fields, api
from odoo.tools.translate import _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time
from pytz import timezone

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

    # Fields used for showing template on a calendar
    start_of_week = fields.Date(compute='_compute_start_of_week')
    date_start = fields.Datetime(compute='_compute_date_start')
    date_end = fields.Datetime(compute='_compute_date_end')

    _order = 'week, dayofweek, hour_from'

    def _rec_message(self):
        return _('Duplicate Records!')

    _sql_constraints = [
        ('unique_template_day_from',
         'UNIQUE(template_id, week, dayofweek, hour_from)', _rec_message),
        ('unique_template_day_to',
         'UNIQUE(template_id, week, dayofweek, hour_to)', _rec_message),
    ]

    
    def _compute_start_of_week(self):
        start_of_week = date.today() - relativedelta(days=date.today().weekday())
        self.start_of_week = fields.Date.to_string(start_of_week)

    def _set_dates(self):

        delta = relativedelta(fields.Datetime.from_string(self.date_start), fields.Date.from_string(self.start_of_week))
        week = delta.weeks
        day = delta.days
        hour = delta.hours + (delta.minutes / 60)
        self.week = week+1
        self.dayofweek = str(day)
        self.hour_from = hour

    def _set_date_end(self):
        print(self.start_of_week, self.date_end)
        delta = relativedelta(fields.Datetime.from_string(self.date_end), fields.Date.from_string(self.start_of_week))
        week = delta.weeks
        day = delta.days
        hour = delta.hours + (delta.minutes / 60)
        self.week = week+1
        self.dayofweek = str(day)
        self.hour_to = hour

    @api.depends('start_of_week', 'week', 'dayofweek', 'hour_from')
    def _compute_date_start(self):
        from_hour, from_minute = divmod(
            self.hour_from * 60, 60)
        user_tz = timezone(self.env.user.tz)
        date_shift_start = fields.Date.from_string(self.start_of_week) + \
            relativedelta(weeks=(self.week - 1)) + \
            relativedelta(days=+(int(self.dayofweek)))
        time_shift_start = datetime.combine(
            date_shift_start, time(int(from_hour), int(from_minute)))
        time_shift_start = user_tz.localize(time_shift_start)
        self.date_start = time_shift_start

    @api.depends('start_of_week', 'week', 'dayofweek', 'hour_to')
    def _compute_date_end(self):
        to_hour, to_minute = divmod(self.hour_to * 60, 60)

        date_shift_end = fields.Date.from_string(self.start_of_week) + \
            relativedelta(weeks=(self.week - 1)) + \
            relativedelta(days=+(int(self.dayofweek)))

        if self.hour_to < self.hour_from:
            date_shift_end = date_shift_end + relativedelta(days=1)
        
        user_tz = timezone(self.env.user.tz)
        time_shift_end = datetime.combine(
            date_shift_end, time(int(to_hour), int(to_minute)))
        time_shift_end = user_tz.localize(time_shift_end)
        self.date_end = time_shift_end
