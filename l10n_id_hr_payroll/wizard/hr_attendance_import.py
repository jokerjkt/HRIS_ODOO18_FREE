# -*- coding: utf-8 -*-
"""
hr.attendance.import.wizard — Wizard Import Absensi
=====================================================
Wizard untuk import data absensi dari mesin atau file CSV/Excel.
"""
import base64
import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrAttendanceImportWizard(models.TransientModel):
    _name = 'hr.attendance.import.wizard'
    _description = 'Wizard Import Absensi'

    source = fields.Selection([
        ('device', 'Dari Mesin (Pull Data)'),
        ('file', 'Upload File (CSV/Excel)'),
    ], string='Sumber Data', required=True, default='file')
    device_id = fields.Many2one(
        'hr.attendance.device', string='Mesin Absensi',
        domain="[('connection_type', '!=', 'csv_import')]",
        help='Pilih mesin untuk pull data langsung',
    )
    file = fields.Binary(string='File Absensi')
    file_name = fields.Char(string='Nama File')
    file_format = fields.Selection([
        ('csv', 'CSV'),
        ('xlsx', 'Excel (.xlsx)'),
        ('dat', 'DAT (Tab separated)'),
    ], string='Format File', default='csv')
    date_from = fields.Date(string='Tanggal Dari', default=fields.Date.today)
    date_to = fields.Date(string='Tanggal Sampai', default=fields.Date.today)
    auto_import = fields.Boolean(
        string='Langsung Import ke Attendance',
        default=True,
        help='Jika dicentang, data akan langsung dibuat sebagai record hr.attendance',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('preview', 'Preview'),
        ('done', 'Selesai'),
    ], default='draft')
    line_ids = fields.One2many(
        'hr.attendance.import.wizard.line', 'wizard_id', string='Preview Data',
    )
    total_parsed = fields.Integer(string='Total Diparse', readonly=True)
    total_matched = fields.Integer(string='Cocok dengan Karyawan', readonly=True)
    total_unmatched = fields.Integer(string='Tidak Cocok', readonly=True)
    total_imported = fields.Integer(string='Berhasil Diimport', readonly=True)
    error_log = fields.Text(string='Error Log', readonly=True)

    @api.constrains('source', 'device_id', 'file')
    def _check_required_fields(self):
        for rec in self:
            if rec.source == 'device' and not rec.device_id:
                raise ValidationError('Pilih mesin absensi!')
            if rec.source == 'file' and not rec.file:
                raise ValidationError('Upload file absensi!')

    def action_parse(self):
        """Parse data dari mesin atau file."""
        self.ensure_one()

        # Clear existing lines
        self.line_ids.unlink()
        self.error_log = False

        try:
            if self.source == 'device':
                logs_data = self._pull_from_device()
            else:
                logs_data = self._parse_uploaded_file()

            if not logs_data:
                raise ValidationError('Tidak ada data yang ditemukan.')

            # Buat preview lines
            total_matched = 0
            total_unmatched = 0

            for data in logs_data:
                emp = self._match_employee(data.get('employee_pin', ''))
                if emp:
                    total_matched += 1
                else:
                    total_unmatched += 1

                punch_display = 'Check In' if data.get('punch_type') == '0' else 'Check Out'
                verify_display = self._get_verify_display(data.get('verify_mode', '1'))

                self.env['hr.attendance.import.wizard.line'].create({
                    'wizard_id': self.id,
                    'employee_id': emp.id if emp else False,
                    'employee_pin': data.get('employee_pin', ''),
                    'timestamp': data.get('timestamp'),
                    'punch_type': data.get('punch_type', '0'),
                    'punch_display': punch_display,
                    'verify_mode': data.get('verify_mode', '1'),
                    'verify_display': verify_display,
                    'state': 'matched' if emp else 'error',
                    'error_message': '' if emp else f"PIN tidak ditemukan: {data.get('employee_pin', '')}",
                    'raw_data': data.get('raw_data', ''),
                })

            self.write({
                'state': 'preview',
                'total_parsed': len(logs_data),
                'total_matched': total_matched,
                'total_unmatched': total_unmatched,
            })

        except Exception as e:
            raise ValidationError(f'Error parsing: {str(e)}')

    def _pull_from_device(self):
        """Pull data dari mesin langsung."""
        if not self.device_id:
            raise ValidationError('Pilih mesin absensi!')

        connector = self.device_id._get_connector()
        return connector.pull_attendance(
            self.device_id,
            date_from=self.date_from,
            date_to=self.date_to,
        )

    def _parse_uploaded_file(self):
        """Parse file yang di-upload."""
        if not self.file:
            raise ValidationError('Upload file absensi!')

        file_content = base64.b64decode(self.file)
        file_name = self.file_name or 'data.csv'

        connector = self.env['hr.attendance.connector.csv']
        return connector.parse_file(file_content, file_name)

    def _match_employee(self, pin):
        """Cocokkan PIN dengan karyawan."""
        if not pin:
            return False

        mapping = 'pin'  # Default
        if self.device_id:
            mapping = self.device_id.employee_mapping

        if mapping == 'pin':
            emp = self.env['hr.employee'].search([
                ('pin', '=', pin),
                ('active', '=', True),
            ], limit=1)
        else:
            emp = self.env['hr.employee'].search([
                ('identification_id', '=', pin),
                ('active', '=', True),
            ], limit=1)

        return emp

    def _get_verify_display(self, mode):
        """Get display name for verify mode."""
        mapping = {
            '0': 'Password', '1': 'Fingerprint', '2': 'Card',
            '3': 'Face', '4': 'Iris',
        }
        return mapping.get(mode, '-')

    def action_import(self):
        """Import data yang sudah di-preview ke hr.attendance."""
        self.ensure_one()
        self.env['hr.payslip']._enforce_trial()

        if self.state != 'preview':
            raise ValidationError('Lakukan parsing terlebih dahulu!')

        imported_count = 0
        error_log = []

        for line in self.line_ids.filtered(lambda l: l.state == 'matched' and l.employee_id):
            try:
                if self.auto_import:
                    # Buat hr.attendance record
                    att_vals = {
                        'employee_id': line.employee_id.id,
                        'check_in': line.timestamp,
                        'punch_type': line.punch_type,
                        'verify_mode': line.verify_mode,
                        'in_mode': 'manual',
                    }
                    if self.device_id:
                        att_vals['device_id'] = self.device_id.id

                    # Jika check out, set check_out juga
                    if line.punch_type == '1':
                        att_vals['check_out'] = line.timestamp

                    att = self.env['hr.attendance'].create(att_vals)

                    # Buat device log juga
                    self.env['hr.attendance.device.log'].create({
                        'device_id': self.device_id.id if self.device_id else False,
                        'employee_id': line.employee_id.id,
                        'employee_pin': line.employee_pin,
                        'timestamp': line.timestamp,
                        'punch_type': line.punch_type,
                        'verify_mode': line.verify_mode,
                        'raw_data': line.raw_data,
                        'state': 'imported',
                        'attendance_id': att.id,
                    })

                    imported_count += 1
                else:
                    # Hanya buat device log, belum import ke attendance
                    self.env['hr.attendance.device.log'].create({
                        'device_id': self.device_id.id if self.device_id else False,
                        'employee_id': line.employee_id.id,
                        'employee_pin': line.employee_pin,
                        'timestamp': line.timestamp,
                        'punch_type': line.punch_type,
                        'verify_mode': line.verify_mode,
                        'raw_data': line.raw_data,
                        'state': 'matched',
                    })
                    imported_count += 1

            except Exception as e:
                error_log.append(f"PIN {line.employee_pin}: {str(e)}")

        self.write({
            'state': 'done',
            'total_imported': imported_count,
            'error_log': '\n'.join(error_log) if error_log else False,
        })

        # Update last_sync device
        if self.device_id:
            self.device_id.last_sync = fields.Datetime.now()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Selesai',
                'message': f'{imported_count} data absensi berhasil diimport.',
                'type': 'success' if not error_log else 'warning',
                'sticky': False,
            }
        }

    def action_reset(self):
        """Reset wizard ke draft."""
        self.ensure_one()
        self.line_ids.unlink()
        self.write({
            'state': 'draft',
            'total_parsed': 0,
            'total_matched': 0,
            'total_unmatched': 0,
            'total_imported': 0,
            'error_log': False,
        })


class HrAttendanceImportWizardLine(models.TransientModel):
    _name = 'hr.attendance.import.wizard.line'
    _description = 'Preview Line Import Absensi'

    wizard_id = fields.Many2one(
        'hr.attendance.import.wizard', string='Wizard',
        required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Karyawan',
    )
    employee_pin = fields.Char(string='User ID (PIN)')
    timestamp = fields.Datetime(string='Waktu')
    punch_type = fields.Selection([
        ('0', 'Check In'),
        ('1', 'Check Out'),
    ], string='Tipe')
    punch_display = fields.Char(string='Tipe Absensi')
    verify_mode = fields.Selection([
        ('0', 'Password'),
        ('1', 'Fingerprint'),
        ('2', 'Card'),
        ('3', 'Face'),
        ('4', 'Iris'),
    ], string='Verifikasi')
    verify_display = fields.Char(string='Metode Verifikasi')
    state = fields.Selection([
        ('matched', 'Cocok'),
        ('error', 'Error'),
    ], string='Status')
    error_message = fields.Char(string='Error')
    raw_data = fields.Text(string='Data Mentah')
