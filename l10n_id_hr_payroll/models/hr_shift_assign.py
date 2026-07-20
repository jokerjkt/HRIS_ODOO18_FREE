# -*- coding: utf-8 -*-
"""
Shift Assign — Assign rotation ke karyawan untuk periode tertentu
=================================================================
"""
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrShiftAssign(models.Model):
    _name = 'hr.shift.assign'
    _description = 'Assign Shift ke Karyawan'
    _order = 'date_from desc, employee_id'
    _inherit = ['trial.mixin']

    employee_id = fields.Many2one(
        'hr.employee', string='Karyawan', required=True,
        domain="[('active', '=', True)]",
    )
    department_id = fields.Many2one(
        'hr.department', related='employee_id.department_id',
        store=True,
    )
    rotation_id = fields.Many2one(
        'hr.shift.rotation', string='Pola Rotasi', required=True,
    )
    date_from = fields.Date(string='Tanggal Mulai', required=True)
    date_to = fields.Date(string='Tanggal Selesai')
    daily_ids = fields.One2many(
        'hr.shift.daily', 'assign_id', string='Jadwal Harian',
    )
    daily_count = fields.Integer(
        string='Total Hari', compute='_compute_daily_count', store=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi'),
        ('done', 'Selesai'),
    ], string='Status', default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        self._enforce_trial()
        return super().create(vals_list)

    @api.depends('daily_ids')
    def _compute_daily_count(self):
        for rec in self:
            rec.daily_count = len(rec.daily_ids)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError('Tanggal mulai tidak boleh setelah tanggal selesai!')

    @api.constrains('employee_id', 'date_from', 'date_to')
    def _check_overlap(self):
        for rec in self:
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('id', '!=', rec.id),
                ('state', '!=', 'done'),
                '|',
                ('date_to', '=', False),
                ('date_to', '>=', rec.date_from),
            ]
            if rec.date_to:
                domain = [
                    ('employee_id', '=', rec.employee_id.id),
                    ('id', '!=', rec.id),
                    ('state', '!=', 'done'),
                    ('date_from', '<=', rec.date_to),
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', rec.date_from),
                ]
            if self.search(domain, limit=1):
                raise ValidationError(
                    f'Karyawan {rec.employee_id.name} sudah memiliki assign shift '
                    f'pada periode tersebut!'
                )

    def action_generate_daily(self):
        """Generate jadwal harian berdasarkan rotasi."""
        self._enforce_trial()
        for rec in self:
            if not rec.rotation_id.line_ids:
                raise ValidationError('Pola rotasi tidak memiliki detail siklus!')
            # Delete existing daily records
            rec.daily_ids.unlink()
            # Get holiday dates
            holiday_dates = self._get_holiday_dates(rec.date_from, rec.date_to)
            # Generate daily records
            end_date = rec.date_to or fields.Date.today() + relativedelta(months=3)
            current_date = rec.date_from
            day_counter = 0
            Daily = self.env['hr.shift.daily']
            lines = rec.rotation_id.line_ids.sorted(key=lambda l: l.day_number)
            while current_date <= end_date:
                day_counter += 1
                # Find which shift in rotation cycle
                cycle_pos = ((day_counter - 1) % rec.rotation_id.cycle_length)
                matching_line = lines[cycle_pos]
                shift_type = matching_line.shift_type_id
                is_holiday = current_date in holiday_dates
                Daily.create({
                    'assign_id': rec.id,
                    'employee_id': rec.employee_id.id,
                    'date': current_date,
                    'shift_type_id': shift_type.id,
                    'is_holiday': is_holiday,
                    'is_rest': shift_type.is_rest,
                })
                current_date += timedelta(days=1)
            rec.state = 'confirmed'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'draft'

    def _get_holiday_dates(self, date_from, date_to):
        """Get semua tanggal hari libur dari resource.calendar.leaves (public holiday)."""
        # Use resource.calendar.leaves for public holidays
        calendar_leaves = self.env['resource.calendar.leaves'].search([])
        holiday_dates = set()
        for leave in calendar_leaves:
            if leave.date_from and leave.date_to:
                current = leave.date_from.date() if hasattr(leave.date_from, 'date') else leave.date_from
                end = leave.date_to.date() if hasattr(leave.date_to, 'date') else leave.date_to
                while current <= end:
                    if date_from <= current <= (date_to or fields.Date.today()):
                        holiday_dates.add(current)
                    current += timedelta(days=1)
            elif leave.date_from:
                d = leave.date_from.date() if hasattr(leave.date_from, 'date') else leave.date_from
                if date_from <= d <= (date_to or fields.Date.today()):
                    holiday_dates.add(d)
        return holiday_dates
