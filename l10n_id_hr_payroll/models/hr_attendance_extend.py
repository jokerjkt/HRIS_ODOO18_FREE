# -*- coding: utf-8 -*-
"""
hr.attendance (extend) — Tambah field device ke Attendance core
================================================================
"""
from odoo import models, fields, api


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    device_id = fields.Many2one(
        'hr.attendance.device', string='Mesin Absensi',
        readonly=True,
        help='Mesin tempat data absensi ini tercatat',
    )
    device_log_id = fields.Many2one(
        'hr.attendance.device.log', string='Log dari Mesin',
        readonly=True,
        help='Log asli dari mesin absensi',
    )
    punch_type = fields.Selection([
        ('0', 'Check In'),
        ('1', 'Check Out'),
    ], string='Tipe Absensi', readonly=True,
        help='Tipe absensi dari mesin (0=Check In, 1=Check Out)',
    )
    verify_mode = fields.Selection([
        ('0', 'Password'),
        ('1', 'Fingerprint'),
        ('2', 'Card'),
        ('3', 'Face'),
        ('4', 'Iris'),
    ], string='Metode Verifikasi', readonly=True,
        help='Metode autentikasi yang digunakan saat absen',
    )
    is_from_device = fields.Boolean(
        string='Dari Mesin',
        compute='_compute_is_from_device',
        store=True,
    )

    @api.depends('device_id')
    def _compute_is_from_device(self):
        for rec in self:
            rec.is_from_device = bool(rec.device_id)
