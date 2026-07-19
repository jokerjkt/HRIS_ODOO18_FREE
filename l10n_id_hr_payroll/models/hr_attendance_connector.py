# -*- coding: utf-8 -*-
"""
hr.attendance.connector — Abstract Base Connector
===================================================
Base class untuk semua koneksi ke mesin absensi.
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrAttendanceConnector(models.AbstractModel):
    _name = 'hr.attendance.connector'
    _description = 'Device Connector (Abstract)'

    def test_connection(self, device):
        """Test koneksi ke device. Return dict: {success, serial_number, firmware, error}"""
        raise ValidationError('Metode test_connection belum diimplementasi.')

    def pull_attendance(self, device, date_from=None, date_to=None):
        """Ambil data attendance dari device. Return list of dicts:
        [{employee_pin, timestamp, punch_type, verify_mode, raw_data}]"""
        raise ValidationError('Metode pull_attendance belum diimplementasi.')

    def sync_time(self, device):
        """Sinkronisasi waktu device dengan server."""
        raise ValidationError('Metode sync_time belum diimplementasi.')

    def _match_employee(self, device, pin):
        """Cocokkan PIN dari device dengan karyawan di Odoo."""
        self.ensure_one()
        if device.employee_mapping == 'pin':
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

    def _create_device_logs(self, device, logs_data):
        """Buat hr.attendance.device.log dari data yang di-pull."""
        self.ensure_one()
        log_model = self.env['hr.attendance.device.log']
        created_logs = []

        for data in logs_data:
            # Cocokkan employee
            emp = self._match_employee(device, data.get('employee_pin', ''))

            # Buat log
            log_vals = {
                'device_id': device.id,
                'employee_id': emp.id if emp else False,
                'employee_pin': data.get('employee_pin', ''),
                'timestamp': data.get('timestamp'),
                'punch_type': data.get('punch_type', '0'),
                'verify_mode': data.get('verify_mode', '1'),
                'raw_data': data.get('raw_data', ''),
                'state': 'matched' if emp else ('error' if not emp else 'pending'),
                'error_message': False if emp else f"PIN tidak ditemukan: {data.get('employee_pin', '')}",
            }
            log = log_model.create(log_vals)
            created_logs.append(log)

        # Update last_sync device
        device.last_sync = fields.Datetime.now()

        return created_logs
