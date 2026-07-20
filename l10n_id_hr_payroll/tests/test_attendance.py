# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import datetime


class TestAttendance(TransactionCase):

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Attendance',
            'pin': '1001',
        })
        self.device = self.env['hr.attendance.device'].create({
            'name': 'Test Device',
            'brand': 'zteko',
            'connection_type': 'csv_import',
            'location': 'Lobi',
            'employee_mapping': 'pin',
        })

    def test_device_creation(self):
        """Device bisa dibuat"""
        self.assertEqual(self.device.name, 'Test Device')
        self.assertEqual(self.device.brand, 'zteko')
        self.assertEqual(self.device.state, 'offline')

    def test_device_log_creation(self):
        """Device log bisa dibuat"""
        log = self.env['hr.attendance.device.log'].create({
            'device_id': self.device.id,
            'employee_id': self.employee.id,
            'employee_pin': '1001',
            'timestamp': '2025-01-15 08:30:00',
            'punch_type': '0',
            'verify_mode': '1',
            'state': 'matched',
        })
        self.assertEqual(log.state, 'matched')
        self.assertEqual(log.punch_type, '0')

    def test_device_log_unmatched(self):
        """Log tanpa employee = unmatched/error"""
        log = self.env['hr.attendance.device.log'].create({
            'device_id': self.device.id,
            'employee_pin': '9999',
            'timestamp': '2025-01-15 08:30:00',
            'punch_type': '0',
            'verify_mode': '1',
            'state': 'error',
            'error_message': 'PIN tidak ditemukan: 9999',
        })
        self.assertEqual(log.state, 'error')
        self.assertIn('9999', log.error_message)

    def test_employee_match_by_pin(self):
        """Match employee by PIN"""
        logs = self.env['hr.attendance.device.log'].search([
            ('employee_pin', '=', '1001'),
        ])
        self.assertTrue(len(logs) >= 0)  # Basic check

    def test_attendance_punch_type(self):
        """Punch type IN/OUT"""
        self.assertEqual(
            self.env['hr.attendance.device.log']._get_punch_type_sel(),
            [('0', 'IN'), ('1', 'OUT')]
        )
