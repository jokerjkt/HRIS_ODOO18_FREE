# -*- coding: utf-8 -*-
"""
hr.attendance.device — Registry Mesin Absensi
===============================================
Menyimpan informasi tentang setiap mesin absensi (fingerprint/RFID)
yang terhubung ke sistem.
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrAttendanceDevice(models.Model):
    _name = 'hr.attendance.device'
    _description = 'Mesin Absensi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nama Mesin', required=True, tracking=True)
    brand = fields.Selection([
        ('zteko', 'ZKTeco'),
        ('solution', 'Solution'),
        ('fingerplus', 'FingerPlus'),
        ('fingerspot', 'Fingerspot'),
        ('essl', 'eSSL'),
        ('att2000', 'ATT2000'),
        ('generic', 'Lainnya'),
    ], string='Merek', required=True, tracking=True)
    connection_type = fields.Selection([
        ('tcp_udp', 'TCP/UDP Direct (PyZK)'),
        ('adms', 'ADMS Cloud Push'),
        ('soap_http', 'SOAP/HTTP API'),
        ('csv_import', 'File Import Only'),
    ], string='Tipe Koneksi', required=True, default='csv_import', tracking=True)
    ip_address = fields.Char(
        string='Alamat IP',
        help='IP address mesin (untuk koneksi TCP/UDP atau ADMS)',
    )
    port = fields.Integer(
        string='Port', default=4370,
        help='Port komunikasi (default ZKTeco: 4370, Solution: 80)',
    )
    comm_key = fields.Char(
        string='Comm Key',
        help='Password komunikasi device (biasanya 0 atau kosong)',
    )
    serial_number = fields.Char(
        string='Serial Number',
        readonly=True,
        help='Serial number mesin (otomatis terisi saat koneksi pertama)',
    )
    firmware_version = fields.Char(
        string='Firmware',
        readonly=True,
    )
    location = fields.Char(
        string='Lokasi',
        help='Lokasi pemasangan mesin',
    )
    assigned_zone_id = fields.Many2one(
        'hr.attendance.geo.fence',
        string='Zona Geofence',
        help='Zona geofence default untuk mesin ini',
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Departemen Terkait',
        help='Departemen yang menggunakan mesin ini',
    )
    employee_mapping = fields.Selection([
        ('pin', 'PIN (field pin di Employee)'),
        ('identification_id', 'Identification ID'),
    ], string='Mapping Karyawan', default='pin',
        help='Field pada hr.employee yang cocok dengan User ID di mesin',
        required=True,
    )
    last_sync = fields.Datetime(string='Terakhir Sync', readonly=True, tracking=True)
    state = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
    ], string='Status', default='offline', tracking=True)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Catatan')
    user_id = fields.Many2one(
        'res.users', string='Penanggung Jawab',
        help='User yang bertanggung jawab atas mesin ini',
    )
    log_ids = fields.One2many(
        'hr.attendance.device.log', 'device_id', string='Log Absensi',
    )
    log_count = fields.Integer(compute='_compute_log_count', string='Jumlah Log')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Nama mesin harus unik!'),
    ]

    def _compute_log_count(self):
        for rec in self:
            rec.log_count = self.env['hr.attendance.device.log'].search_count([
                ('device_id', '=', rec.id),
            ])

    def action_test_connection(self):
        """Test koneksi ke mesin."""
        self.ensure_one()
        if self.connection_type == 'csv_import':
            raise ValidationError('Mesin ini hanya mendukung import file, tidak perlu test koneksi.')
        if not self.ip_address:
            raise ValidationError('Alamat IP harus diisi terlebih dahulu!')

        try:
            connector = self._get_connector()
            result = connector.test_connection(self)
            if result.get('success'):
                self.write({
                    'state': 'online',
                    'serial_number': result.get('serial_number', ''),
                    'firmware_version': result.get('firmware', ''),
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Koneksi Berhasil',
                        'message': f"Mesin '{self.name}' terdeteksi online. "
                                   f"SN: {result.get('serial_number', '-')}",
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                self.state = 'error'
                raise ValidationError(f"Gagal koneksi: {result.get('error', 'Unknown error')}")
        except Exception as e:
            self.state = 'error'
            raise ValidationError(f"Error koneksi: {str(e)}")

    def action_pull_attendance(self):
        """Ambil data absensi dari mesin."""
        self.ensure_one()
        if self.connection_type == 'csv_import':
            raise ValidationError('Mesin ini hanya mendukung import file.')

        wizard = self.env['hr.attendance.import.wizard'].create({
            'device_id': self.id,
            'source': 'device',
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import Absensi dari Mesin',
            'res_model': 'hr.attendance.import.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_view_logs(self):
        """Lihat log absensi dari mesin ini."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Log Absensi — {self.name}',
            'res_model': 'hr.attendance.device.log',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }

    def _get_connector(self):
        """Get connector instance berdasarkan tipe koneksi."""
        self.ensure_one()
        mapping = {
            'tcp_udp': 'hr.attendance.connector.zkteco',
            'adms': 'hr.attendance.connector.zkteco',
            'soap_http': 'hr.attendance.connector.solution',
            'csv_import': 'hr.attendance.connector.csv',
        }
        model_name = mapping.get(self.connection_type)
        if not model_name:
            raise ValidationError(f'Tipe koneksi "{self.connection_type}" belum didukung.')
        return self.env[model_name]

    def action_set_offline(self):
        for rec in self:
            rec.state = 'offline'
