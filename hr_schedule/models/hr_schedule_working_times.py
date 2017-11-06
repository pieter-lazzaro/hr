from odoo import models, fields, api
from odoo.tools.translate import _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time
from pytz import timezone, utc

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
    date_start = fields.Datetime(
        compute='_compute_date_start', inverse='_set_dates')
    date_end = fields.Datetime(
        compute='_compute_date_end', inverse='_set_dates')

    _order = 'week, dayofweek, hour_from'

    def _rec_message(self):
        return _('Duplicate Records!')

    _sql_constraints = [
        ('unique_template_day_from',
         'CHECK(1=1)', _rec_message),
        ('unique_template_day_to',
         'CHECK(1=1)', _rec_message),
    ]

    @api.model
    def get_start_of_week(self, today):
        day = today.weekday()
        # Push sundays into the next week
        if day == 6:
            day = -1
        return today - relativedelta(days=day)
    
    def _compute_start_of_week(self):
        for record in self:
            start_of_week = self.get_start_of_week(date.today())
            record.start_of_week = fields.Date.to_string(start_of_week)

    @api.model
    def default_get(self, fields):
        
        defaults = super(hr_schedule_working_times, self).default_get(fields)

        if 'hour_from' in fields and 'hour_from' not in defaults:
            defaults = self.convert_dates_to_schedule(defaults)
        
        return defaults

    @api.multi
    def _set_dates(self):

        for record in self:
            vals = self.convert_dates_to_schedule({
                'date_start': record.date_start,
                'date_end': record.date_end,
                'start_of_week': record.start_of_week,
            })
            
            record.week = vals['week']
            record.dayofweek = vals['dayofweek']
            record.hour_from = vals['hour_from']
            record.hour_to = vals['hour_to']

    def convert_dates_to_schedule(self, vals):
        user_tz = timezone(self.env.user.tz)

        if 'start_of_week' not in vals:
            vals['start_of_week'] = fields.Datetime.to_string(self.get_start_of_week(date.today()))
        
        
        start_of_week = user_tz.localize(fields.Datetime.from_string(vals['start_of_week']))

        date_start = fields.Datetime.from_string(vals['date_start'])
        date_end = fields.Datetime.from_string(vals['date_end'])
        date_start = utc.localize(date_start).astimezone(user_tz)
        date_end = utc.localize(date_end).astimezone(user_tz)
        
        start_delta = relativedelta(date_start, start_of_week)
        week = start_delta.weeks
        day = start_delta.days - (week * 7)
        
        vals['week'] = week + 1
        vals['dayofweek'] = str(day)
        vals['hour_from'] = date_start.hour + (date_start.minute / 60)
        vals['hour_to'] = date_end.hour + (date_end.minute / 60)

        return vals

    @api.depends('start_of_week', 'week', 'dayofweek', 'hour_from')
    def _compute_date_start(self):
        for record in self:
            record.date_start = record.get_date_start(fields.Date.from_string(record.start_of_week))

    @api.multi
    def get_date_start(self, start_of_schedule):
        self.ensure_one()
        from_hour, from_minute = divmod(
            self.hour_from * 60, 60)
        user_tz = timezone(self.env.user.tz)
        date_shift_start = start_of_schedule + \
            relativedelta(weeks=(self.week - 1)) + \
            relativedelta(days=+(int(self.dayofweek)))
        time_shift_start = datetime.combine(
            date_shift_start, time(int(from_hour), int(from_minute)))
        time_shift_start = user_tz.localize(time_shift_start)
        return time_shift_start.astimezone(utc)

    @api.depends('start_of_week', 'week', 'dayofweek', 'hour_to')
    def _compute_date_end(self):
        for record in self:
            record.date_end = record.get_date_end(fields.Date.from_string(record.start_of_week))

    @api.multi
    def get_date_end(self, start_of_schedule):
        self.ensure_one()
        to_hour, to_minute = divmod(self.hour_to * 60, 60)

        date_shift_end = start_of_schedule + \
            relativedelta(weeks=(self.week - 1)) + \
            relativedelta(days=+(int(self.dayofweek)))

        if self.hour_to < self.hour_from:
            date_shift_end = date_shift_end + relativedelta(days=1)

        user_tz = timezone(self.env.user.tz)
        time_shift_end = datetime.combine(
            date_shift_end, time(int(to_hour), int(to_minute)))
        time_shift_end = user_tz.localize(time_shift_end)
        return time_shift_end.astimezone(utc)

    @api.model
    def create(self, vals):

        if 'template_id' not in vals and self.env.context.get('active_model') == "hr.schedule.template" and self.env.context.get('active_id'):
            vals['template_id'] = self.env.context['active_id']
        
        if 'date_start' in vals and 'date_end' in vals:
            vals = self.convert_dates_to_schedule(vals)
        
        return super(hr_schedule_working_times, self).create(vals)
