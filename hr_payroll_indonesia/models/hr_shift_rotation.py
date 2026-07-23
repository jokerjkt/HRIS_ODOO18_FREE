# -*- coding: utf-8 -*-
"""
Shift Rotation — Pola rotasi shift (3-shift weekly, 4-shift daily)
===================================================================
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrShiftRotation(models.Model):
    _name = 'hr.shift.rotation'
    _description = 'Pola Rotasi Shift'
    _order = 'name'

    name = fields.Char(string='Nama Pola', required=True)
    rotation_type = fields.Selection([
        ('3_shift_weekly', '3-Shift (Pagi-Siang-Malam) Weekly'),
        ('4_shift_daily', '4-Shift (Pagi-Siang-Malam-Libur) Daily'),
        ('custom', 'Custom'),
    ], string='Tipe Rotasi', required=True, default='3_shift_weekly')
    cycle_length = fields.Integer(
        string='Panjang Siklus (hari)',
        compute='_compute_cycle_length',
        store=True,
    )
    line_ids = fields.One2many(
        'hr.shift.rotation.line', 'rotation_id',
        string='Detail Siklus',
        copy=True,
    )
    note = fields.Text(string='Keterangan')
    active = fields.Boolean(default=True)

    @api.depends('line_ids')
    def _compute_cycle_length(self):
        for rec in self:
            rec.cycle_length = len(rec.line_ids)

    @api.constrains('line_ids')
    def _check_lines(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError('Pola rotasi harus memiliki minimal 1 hari siklus!')
            day_numbers = rec.line_ids.mapped('day_number')
            if len(day_numbers) != len(set(day_numbers)):
                raise ValidationError('Nomor hari dalam siklus tidak boleh duplikat!')

    def action_copy_template_3shift(self):
        """Copy template 3-shift weekly ke pola custom."""
        self.ensure_one()
        if self.line_ids:
            raise ValidationError('Pola sudah memiliki data! Hapus dulu sebelum copy template.')
        ShiftType = self.env['hr.shift.type']
        pagi = ShiftType.search([('code', '=', 'P')], limit=1)
        siang = ShiftType.search([('code', '=', 'S')], limit=1)
        malam = ShiftType.search([('code', '=', 'M')], limit=1)
        libur = ShiftType.search([('code', '=', 'L')], limit=1)
        if not all([pagi, siang, malam, libur]):
            raise ValidationError('Tipe shift default belum lengkap! Jalankan data seed terlebih dahulu.')
        template = [
            (1, pagi.id), (2, pagi.id), (3, siang.id),
            (4, siang.id), (5, malam.id), (6, malam.id),
            (7, libur.id),
        ]
        for day_num, shift_id in template:
            self.env['hr.shift.rotation.line'].create({
                'rotation_id': self.id,
                'day_number': day_num,
                'shift_type_id': shift_id,
            })
        self.rotation_type = '3_shift_weekly'

    def action_copy_template_4shift(self):
        """Copy template 4-shift daily ke pola custom."""
        self.ensure_one()
        if self.line_ids:
            raise ValidationError('Pola sudah memiliki data! Hapus dulu sebelum copy template.')
        ShiftType = self.env['hr.shift.type']
        pagi = ShiftType.search([('code', '=', 'P')], limit=1)
        siang = ShiftType.search([('code', '=', 'S')], limit=1)
        malam = ShiftType.search([('code', '=', 'M')], limit=1)
        libur = ShiftType.search([('code', '=', 'L')], limit=1)
        if not all([pagi, siang, malam, libur]):
            raise ValidationError('Tipe shift default belum lengkap! Jalankan data seed terlebih dahulu.')
        template = [
            (1, pagi.id), (2, siang.id), (3, malam.id), (4, libur.id),
        ]
        for day_num, shift_id in template:
            self.env['hr.shift.rotation.line'].create({
                'rotation_id': self.id,
                'day_number': day_num,
                'shift_type_id': shift_id,
            })
        self.rotation_type = '4_shift_daily'


class HrShiftRotationLine(models.Model):
    _name = 'hr.shift.rotation.line'
    _description = 'Detail Siklus Rotasi Shift'
    _order = 'rotation_id, day_number'

    rotation_id = fields.Many2one(
        'hr.shift.rotation', string='Pola Rotasi',
        required=True, ondelete='cascade',
    )
    day_number = fields.Integer(string='Hari ke-', required=True)
    shift_type_id = fields.Many2one(
        'hr.shift.type', string='Tipe Shift', required=True,
    )
    shift_code = fields.Char(related='shift_type_id.code', string='Kode', store=True)
    shift_color = fields.Integer(related='shift_type_id.color', string='Warna')
