from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools.profiler import profile
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
    start_of_week = fields.Datetime(compute='_compute_start_of_week')

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
        today = self.normalize_date(today)

        day = today.weekday()
        
        # Push sundays into the next week
        if day == 6:
            day = -1
        start_of_week = today - relativedelta(days=day)
        
        start_of_week = start_of_week - self._get_dst_offset(start_of_week, today)

        return start_of_week

    def _compute_start_of_week(self):
        for record in self:
            record.start_of_week = self._get_default_start_of_week()

    def _get_default_start_of_week(self):
        user_tz = timezone(self.env.user.tz)
        today = datetime.today()
        today = user_tz.localize(datetime(today.year, today.month, today.day))

        return fields.Datetime.to_string(self.get_start_of_week(today).astimezone(utc))

    def _get_dst_offset(self, start, end):
        ''' Checks of daylight savings changes between start and end. '''
        
        user_tz = timezone(self.env.user.tz)
        start_time = start.astimezone(user_tz)
        end_time = end.astimezone(user_tz)
        
        # DST starts
        if start_time.dst() < end_time.dst():
            return end_time.dst() * -1
        
        # DST ends
        if start_time.dst() > end_time.dst():
            return start_time.dst()
        
        return relativedelta(minutes=0)

    def normalize_date(self, timestamp):
        '''
        Return a UTC datetime with timezone information for timestamp.
        - If timestamp is a string it is interpreted as a UTC Odoo timestamp
        - If timestamp is a date it is converted to a 00:00:00 on that date in the users timezone
          and then converted to UTC
        - If timestamp is already a datetime but doesn't have a timezone it will be localized to UTC
        '''
        user_tz = timezone(self.env.user.tz)

        if isinstance(timestamp, date):
            localized = user_tz.localize(
                datetime(timestamp.year, timestamp.month, timestamp.day))
            return localized.astimezone(utc)
        elif isinstance(timestamp, str):
            localized = utc.localize(fields.Datetime.from_string(timestamp))
            return localized
        elif isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                return utc.localize(timestamp)
            return timestamp.astimezone(utc)

    @api.model
    def default_get(self, wanted_fields):

        defaults = super(hr_schedule_working_times,
                         self).default_get(wanted_fields)
        default_dates = {}

        # Handle the computed fields manually
        if 'default_date_start' in self.env.context:
            default_dates['date_start'] = self.env.context['default_date_start']
        if 'default_date_end' in self.env.context:
            default_dates['date_end'] = self.env.context['default_date_end']
        if 'default_start_of_week' in self.env.context:
            default_dates['start_of_week'] = self.env.context['default_start_of_week']

        if 'start_of_week' not in default_dates:
            default_dates['start_of_week'] = self._get_default_start_of_week()

        if 'date_start' not in default_dates:
            default_dates['date_start'] = default_dates['start_of_week']

        if 'date_end' not in default_dates:
            default_dates['date_end'] = default_dates['date_start']

        computed_defaults = self.convert_dates_to_schedule(default_dates)
        for k in wanted_fields:
            if k in computed_defaults:
                defaults[k] = computed_defaults[k]
        return defaults

    @api.multi
    def _set_dates(self):

        for record in self:
            vals = self.convert_dates_to_schedule({
                'date_start': record.date_start,
                'date_end': record.date_end,
                'start_of_week': record.start_of_week,
            })
            record.write(vals)

    def convert_dates_to_schedule(self, vals):
        user_tz = timezone(self.env.user.tz)

        if 'start_of_week' not in vals:
            vals['start_of_week'] = self._get_default_start_of_week()

        start_of_week = utc.localize(
            fields.Datetime.from_string(vals['start_of_week']))

        date_start = fields.Datetime.from_string(vals['date_start'])
        date_end = fields.Datetime.from_string(vals['date_end'])
        date_start = utc.localize(date_start).astimezone(user_tz)
        date_end = utc.localize(date_end).astimezone(user_tz)

        start_delta = relativedelta(date_start, start_of_week)
        week = start_delta.weeks
        day = start_delta.days - (week * 7)

        del vals['date_start']
        del vals['date_end']
        del vals['start_of_week']

        vals['week'] = week + 1
        vals['dayofweek'] = str(day)
        vals['hour_from'] = date_start.hour + (date_start.minute / 60)
        vals['hour_to'] = date_end.hour + (date_end.minute / 60)

        return vals

    @api.depends('start_of_week', 'week', 'dayofweek', 'hour_from')
    def _compute_date_start(self):
        for record in self:
            record.date_start = record.get_date_start(
                fields.Datetime.from_string(record.start_of_week))

    @api.multi
    def get_date_start(self, start_of_schedule):
        self.ensure_one()

        start_of_schedule = self.normalize_date(start_of_schedule)

        from_hour, from_minute = divmod(self.hour_from * 60, 60)

        weeks = self.week - 1
        days = int(self.dayofweek)
        hours = int(from_hour)
        minutes = int(from_minute)

        time_shift_start = start_of_schedule + relativedelta(weeks=weeks, days=days, hours=hours, minutes=minutes)

        time_shift_start = time_shift_start + self._get_dst_offset(start_of_schedule, time_shift_start)

        return time_shift_start

    @api.depends('start_of_week', 'week', 'dayofweek', 'hour_to')
    def _compute_date_end(self):
        for record in self:
            record.date_end = record.get_date_end(
                fields.Datetime.from_string(record.start_of_week))

    @api.multi
    def get_date_end(self, start_of_schedule):
        self.ensure_one()

        start_of_schedule = self.normalize_date(start_of_schedule)

        to_hour, to_minute = divmod(self.hour_to * 60, 60)

        time_shift_end = start_of_schedule + \
            relativedelta(weeks=(self.week - 1)) + \
            relativedelta(days=+(int(self.dayofweek)))

        if self.hour_to < self.hour_from:
            time_shift_end = time_shift_end + relativedelta(days=1)

        time_shift_end = time_shift_end + \
            relativedelta(hours=int(to_hour), minutes=int(to_minute))

        time_shift_end = time_shift_end + self._get_dst_offset(start_of_schedule, time_shift_end)
        return time_shift_end

    @api.model
    def create(self, vals):

        if 'template_id' not in vals and self.env.context.get('active_model') == "hr.schedule.template" and self.env.context.get('active_id'):
            vals['template_id'] = self.env.context['active_id']

        if 'date_start' in vals and 'date_end' in vals:
            vals = self.convert_dates_to_schedule(vals)

        return super(hr_schedule_working_times, self).create(vals)
