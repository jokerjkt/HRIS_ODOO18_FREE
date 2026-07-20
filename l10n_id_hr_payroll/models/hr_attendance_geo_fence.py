# -*- coding: utf-8 -*-
"""
hr.attendance.geo.fence — Zona Geofence untuk Absensi
======================================================
Memungkinkan perusahaan mendefinisikan zona lokasi (geofence)
dengan koordinat GPS dan radius untuk validasi absensi.
"""
import math
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrAttendanceGeoFence(models.Model):
    _name = 'hr.attendance.geo.fence'
    _description = 'Zona Geofence Absensi'
    _order = 'name'

    name = fields.Char(string='Nama Zona', required=True, tracking=True)
    code = fields.Char(string='Kode Zona', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Perusahaan',
        default=lambda self: self.env.company,
        required=True,
    )
    latitude = fields.Float(
        string='Lintang (Latitude)',
        digits=(10, 7),
        required=True,
        help='Koordinat lintang pusat zona (derajat desimal)',
    )
    longitude = fields.Float(
        string='Bujur (Longitude)',
        digits=(10, 7),
        required=True,
        help='Koordinat bujur pusat zona (derajat desimal)',
    )
    radius_m = fields.Integer(
        string='Radius (meter)',
        default=100,
        required=True,
        help='Jarak maksimum dari pusat zona yang dianggap valid',
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Departemen Terkait',
        help='Departemen yang berwenang di zona ini (kosongkan = semua)',
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Karyawan Terdaftar',
        help='Karyawan yang ditugaskan di zona ini (kosongkan = semua)',
    )
    active = fields.Boolean(default=True, tracking=True)
    note = fields.Text(string='Catatan')
    attendance_device_ids = fields.One2many(
        'hr.attendance.device', 'assigned_zone_id',
        string='Mesin Terkait',
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)',
         'Kode zona harus unik per perusahaan!'),
    ]

    @api.constrains('latitude')
    def _check_latitude(self):
        for rec in self:
            if not (-90 <= rec.latitude <= 90):
                raise ValidationError(
                    'Lintang harus antara -90 dan 90 derajat!'
                )

    @api.constrains('longitude')
    def _check_longitude(self):
        for rec in self:
            if not (-180 <= rec.longitude <= 180):
                raise ValidationError(
                    'Bujur harus antara -180 dan 180 derajat!'
                )

    @api.constrains('radius_m')
    def _check_radius(self):
        for rec in self:
            if rec.radius_m <= 0:
                raise ValidationError('Radius harus lebih besar dari 0!')

    @api.model
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Hitung jarak antara dua titik GPS dalam meter menggunakan Haversine formula."""
        R = 6371000  # radius bumi dalam meter
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def check_point_inside(self, latitude, longitude):
        """Cek apakah titik berada di dalam zona ini. Returns True jika di dalam."""
        self.ensure_one()
        distance = self.haversine_distance(
            self.latitude, self.longitude, latitude, longitude
        )
        return distance <= self.radius_m

    def find_zone_for_point(self, latitude, longitude, employee=None):
        """Cari zona yang cocok untuk titik GPS tertentu.
        Returns zona pertama yang cocok, atau False jika tidak ada."""
        domain = [('active', '=', True)]
        if employee:
            domain += [
                '|',
                ('employee_ids', '=', False),
                ('employee_ids', '=', employee.id),
            ]
        zones = self.search(domain)
        for zone in zones:
            if zone.check_point_inside(latitude, longitude):
                return zone
        return False
