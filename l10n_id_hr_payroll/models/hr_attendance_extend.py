# -*- coding: utf-8 -*-
"""
hr.attendance (extend) — Tambah field device + GPS + Photo + Mobile
======================================================================
"""
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


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

    # ── GPS Fields ────────────────────────────────────────────────────────
    check_in_latitude = fields.Float(
        string='Lintang Masuk', digits=(10, 7),
        help='Koordinat GPS saat check-in',
    )
    check_in_longitude = fields.Float(
        string='Bujur Masuk', digits=(10, 7),
        help='Koordinat GPS saat check-in',
    )
    check_out_latitude = fields.Float(
        string='Lintang Keluar', digits=(10, 7),
        help='Koordinat GPS saat check-out',
    )
    check_out_longitude = fields.Float(
        string='Bujur Keluar', digits=(10, 7),
        help='Koordinat GPS saat check-out',
    )
    check_in_zone_id = fields.Many2one(
        'hr.attendance.geo.fence', string='Zona Masuk',
        readonly=True,
        help='Zona geofence saat check-in',
    )
    check_out_zone_id = fields.Many2one(
        'hr.attendance.geo.fence', string='Zona Keluar',
        readonly=True,
        help='Zona geofence saat check-out',
    )
    is_check_in_inside = fields.Boolean(
        string='Masuk Dalam Zona',
        compute='_compute_fence_status',
        store=True,
    )
    is_check_out_inside = fields.Boolean(
        string='Keluar Dalam Zona',
        compute='_compute_fence_status',
        store=True,
    )

    # ── GPS Accuracy ──────────────────────────────────────────────────────
    check_in_accuracy = fields.Float(
        string='Akurasi GPS Masuk (m)',
        help='Akurasi GPS dalam meter saat check-in',
    )
    check_out_accuracy = fields.Float(
        string='Akurasi GPS Keluar (m)',
        help='Akurasi GPS dalam meter saat check-out',
    )

    # ── Photo / Selfie ────────────────────────────────────────────────────
    check_in_photo = fields.Image(
        string='Foto Check In',
        max_width=640, max_height=640,
        help='Selfie saat check-in',
    )
    check_out_photo = fields.Image(
        string='Foto Check Out',
        max_width=640, max_height=640,
        help='Selfie saat check-out',
    )

    # ── Device Type ───────────────────────────────────────────────────────
    device_type = fields.Selection([
        ('desktop', 'Desktop/Kiosk'),
        ('mobile', 'Mobile/PWA'),
        ('machine', 'Mesin Absensi'),
        ('api', 'API Integration'),
    ], string='Tipe Device', default='desktop',
        help='Device yang digunakan untuk absensi',
    )
    check_in_device_info = fields.Text(
        string='Info Device Masuk',
        help='User agent / device info saat check-in',
    )
    check_out_device_info = fields.Text(
        string='Info Device Keluar',
        help='User agent / device info saat check-out',
    )

    @api.depends('device_id')
    def _compute_is_from_device(self):
        for rec in self:
            rec.is_from_device = bool(rec.device_id)

    @api.depends('check_in_zone_id', 'check_out_zone_id')
    def _compute_fence_status(self):
        for rec in self:
            rec.is_check_in_inside = bool(rec.check_in_zone_id)
            rec.is_check_out_inside = bool(rec.check_out_zone_id)

    @api.model_create_multi
    def create(self, vals_list):
        attendance = super().create(vals_list)
        for rec in attendance:
            rec._validate_geo_fence()
        return attendance

    def write(self, vals):
        result = super().write(vals)
        if 'check_in_latitude' in vals or 'check_in_longitude' in vals:
            for rec in self:
                if rec.check_in_latitude and rec.check_in_longitude:
                    zone = self.env['hr.attendance.geo.fence'].find_zone_for_point(
                        rec.check_in_latitude, rec.check_in_longitude, rec.employee_id
                    )
                    rec.check_in_zone_id = zone.id if zone else False
        if 'check_out_latitude' in vals or 'check_out_longitude' in vals:
            for rec in self:
                if rec.check_out_latitude and rec.check_out_longitude:
                    zone = self.env['hr.attendance.geo.fence'].find_zone_for_point(
                        rec.check_out_latitude, rec.check_out_longitude, rec.employee_id
                    )
                    rec.check_out_zone_id = zone.id if zone else False
        return result

    def _validate_geo_fence(self):
        """Validasi geo-fence saat attendance dibuat."""
        for rec in self:
            if rec.check_in_latitude and rec.check_in_longitude:
                zone = self.env['hr.attendance.geo.fence'].find_zone_for_point(
                    rec.check_in_latitude, rec.check_in_longitude, rec.employee_id
                )
                rec.check_in_zone_id = zone.id if zone else False
                if not zone:
                    _logger.warning(
                        'Attendance check-in for %s at (%s, %s) is OUTSIDE all geo-fence zones',
                        rec.employee_id.name, rec.check_in_latitude, rec.check_in_longitude,
                    )
            if rec.check_out_latitude and rec.check_out_longitude:
                zone = self.env['hr.attendance.geo.fence'].find_zone_for_point(
                    rec.check_out_latitude, rec.check_out_longitude, rec.employee_id
                )
                rec.check_out_zone_id = zone.id if zone else False
                if not zone:
                    _logger.warning(
                        'Attendance check-out for %s at (%s, %s) is OUTSIDE all geo-fence zones',
                        rec.employee_id.name, rec.check_out_latitude, rec.check_out_longitude,
                    )
