# -*- coding: utf-8 -*-
"""
hr.attendance.device.log — Log Raw Absensi dari Mesin
======================================================
Menyimpan data absensi mentah sebelum diproses menjadi hr.attendance.
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrAttendanceDeviceLog(models.Model):
    _name = 'hr.attendance.device.log'
    _description = 'Log Absensi dari Mesin'
    _order = 'timestamp desc, id desc'
    _rec_name = 'display_name'

    device_id = fields.Many2one(
        'hr.attendance.device', string='Mesin',
        required=True, ondelete='cascade', index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Karyawan',
        index=True,
        help='Karyawan yang cocok (otomatis atau manual)',
    )
    employee_pin = fields.Char(
        string='User ID (dari Mesin)',
        index=True,
        help='Nomor ID karyawan seperti tercatat di mesin absensi',
    )
    timestamp = fields.Datetime(
        string='Waktu Absensi', required=True, index=True,
    )
    punch_type = fields.Selection([
        ('0', 'Check In'),
        ('1', 'Check Out'),
        ('2', 'Break Out'),
        ('3', 'Break In'),
        ('4', 'Overtime In'),
        ('5', 'Overtime Out'),
    ], string='Tipe', default='0', required=True)
    punch_type_display = fields.Char(
        compute='_compute_punch_type_display', string='Tipe Absensi',
    )
    verify_mode = fields.Selection([
        ('0', 'Password'),
        ('1', 'Fingerprint'),
        ('2', 'Card'),
        ('3', 'Face'),
        ('4', 'Iris'),
    ], string='Verifikasi')
    verify_mode_display = fields.Char(
        compute='_compute_verify_mode_display', string='Metode Verifikasi',
    )
    raw_data = fields.Text(
        string='Data Mentah',
        help='Data asli dari mesin sebelum diparsing',
    )
    state = fields.Selection([
        ('pending', 'Belum Diproses'),
        ('matched', 'Tcocok dengan Karyawan'),
        ('imported', 'Sudah Diimport'),
        ('error', 'Error'),
    ], string='Status', default='pending', index=True, tracking=True)
    attendance_id = fields.Many2one(
        'hr.attendance', string='Attendance Record',
        readonly=True,
        help='Record hr.attendance yang dibuat dari log ini',
    )
    error_message = fields.Char(string='Pesan Error', readonly=True)
    display_name = fields.Char(
        compute='_compute_display_name', string='Nama Tampilan',
    )

    @api.depends('punch_type')
    def _compute_punch_type_display(self):
        mapping = dict(self._fields['punch_type'].selection)
        for rec in self:
            rec.punch_type_display = mapping.get(rec.punch_type, '-')

    @api.depends('verify_mode')
    def _compute_verify_mode_display(self):
        mapping = dict(self._fields['verify_mode'].selection)
        for rec in self:
            rec.verify_mode_display = mapping.get(rec.verify_mode, '-')

    @api.depends('employee_id', 'employee_pin', 'timestamp', 'punch_type')
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name if rec.employee_id else f"PIN:{rec.employee_pin or '?'}"
            ts = fields.Datetime.context_timestamp(rec, rec.timestamp).strftime('%d %b %Y %H:%M') if rec.timestamp else '-'
            pt = dict(rec._fields['punch_type'].selection).get(rec.punch_type, '?')
            rec.display_name = f"{emp} — {ts} ({pt})"

    def action_match_employee(self):
        """Coba cocokkan log dengan karyawan berdasarkan PIN."""
        for log in self.filtered(lambda l: not l.employee_id and l.employee_pin):
            device = log.device_id
            if device.employee_mapping == 'pin':
                emp = self.env['hr.employee'].search([
                    ('pin', '=', log.employee_pin),
                    ('active', '=', True),
                ], limit=1)
            else:
                emp = self.env['hr.employee'].search([
                    ('identification_id', '=', log.employee_pin),
                    ('active', '=', True),
                ], limit=1)
            if emp:
                log.employee_id = emp.id
                log.state = 'matched'
            else:
                log.state = 'error'
                log.error_message = f"Tidak ditemukan karyawan dengan PIN/User ID: {log.employee_pin}"

    def action_import_to_attendance(self):
        """Import log ini ke hr.attendance."""
        for log in self.filtered(lambda l: l.state in ('matched', 'pending') and l.employee_id):
            # Cek apakah sudah ada attendance yang cocok
            existing = self.env['hr.attendance'].search([
                ('employee_id', '=', log.employee_id.id),
                ('check_in', '>=', fields.Datetime.to_string(log.timestamp.replace(hour=0, minute=0, second=0))),
                ('check_in', '<=', fields.Datetime.to_string(log.timestamp.replace(hour=23, minute=59, second=59))),
            ], limit=1)

            if existing:
                # Update existing attendance
                if log.punch_type == '0':  # Check In
                    existing.check_in = log.timestamp
                elif log.punch_type == '1':  # Check Out
                    existing.check_out = log.timestamp
                log.attendance_id = existing.id
            else:
                # Buat attendance baru
                vals = {
                    'employee_id': log.employee_id.id,
                    'check_in': log.timestamp,
                    'device_id': log.device_id.id,
                    'device_log_id': log.id,
                    'punch_type': log.punch_type,
                    'verify_mode': log.verify_mode,
                    'in_mode': 'manual',
                }
                if log.punch_type == '1':  # Check Out
                    vals['check_out'] = log.timestamp
                att = self.env['hr.attendance'].create(vals)
                log.attendance_id = att.id

            log.state = 'imported'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Selesai',
                'message': f'{len(self.filtered(lambda l: l.state == "imported"))} log berhasil diimport.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_import_all_pending(self):
        """Import semua log pending yang sudah matched."""
        pending = self.search([
            ('state', '=', 'matched'),
            ('employee_id', '!=', False),
        ])
        if pending:
            pending.action_import_to_attendance()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Batch Selesai',
                'message': f'{len(pending)} log berhasil diimport ke attendance.',
                'type': 'success',
                'sticky': False,
            }
        }
