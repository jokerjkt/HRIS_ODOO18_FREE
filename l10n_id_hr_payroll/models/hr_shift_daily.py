# -*- coding: utf-8 -*-
"""
Shift Daily — Generated daily shift records
=============================================
"""
from odoo import models, fields, api


class HrShiftDaily(models.Model):
    _name = 'hr.shift.daily'
    _description = 'Jadwal Harian Shift'
    _order = 'date, employee_id'
    _rec_name = 'display_name'

    assign_id = fields.Many2one(
        'hr.shift.assign', string='Assign Shift',
        required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Karyawan', required=True,
    )
    department_id = fields.Many2one(
        'hr.department', related='assign_id.department_id',
        store=True,
    )
    date = fields.Date(string='Tanggal', required=True)
    shift_type_id = fields.Many2one(
        'hr.shift.type', string='Tipe Shift', required=True,
    )
    shift_name = fields.Char(related='shift_type_id.name', string='Nama Shift')
    shift_code = fields.Char(related='shift_type_id.code', string='Kode Shift', store=True)
    shift_color = fields.Integer(related='shift_type_id.color', string='Warna')
    hour_from = fields.Float(related='shift_type_id.hour_from', string='Jam Mulai')
    hour_to = fields.Float(related='shift_type_id.hour_to', string='Jam Selesai')
    is_holiday = fields.Boolean(string='Hari Libur Nasional', default=False)
    is_rest = fields.Boolean(string='Hari Libur (Rotasi)', default=False)
    is_weekend = fields.Boolean(string='Akhir Pekan', compute='_compute_is_weekend', store=True)
    work_entry_id = fields.Many2one(
        'hr.work.entry', string='Work Entry', readonly=True,
    )
    note = fields.Text(string='Catatan')

    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name', store=True,
    )

    @api.depends('employee_id', 'date', 'shift_type_id')
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or ''
            date = rec.date.strftime('%d/%m') if rec.date else ''
            shift = rec.shift_type_id.name or ''
            rec.display_name = f'{emp} | {date} | {shift}'

    @api.depends('date')
    def _compute_is_weekend(self):
        for rec in self:
            if rec.date:
                rec.is_weekend = rec.date.weekday() in (5, 6)  # Saturday, Sunday
            else:
                rec.is_weekend = False

    @api.depends('date')
    def _compute_day_of_week(self):
        day_names = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
        for rec in self:
            if rec.date:
                rec.day_of_week = day_names[rec.date.weekday()]
            else:
                rec.day_of_week = ''
