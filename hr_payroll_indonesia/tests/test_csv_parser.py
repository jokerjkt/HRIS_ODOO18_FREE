# -*- coding: utf-8 -*-
import io
import csv
from odoo.tests.common import TransactionCase
from ..models.hr_attendance_connector_csv import HrAttendanceConnectorCsv


class TestCsvParser(TransactionCase):

    def setUp(self):
        super().setUp()
        self.connector = self.env['hr.attendance.connector.csv']

    def _make_csv(self, rows):
        buf = io.StringIO()
        writer = csv.writer(buf)
        for row in rows:
            writer.writerow(row)
        buf.seek(0)
        return buf

    def test_auto_detect_zkteco(self):
        """Auto-detect ZKTeco columns"""
        csv_data = self._make_csv([
            ['SN', 'Name', 'EnrollNumber', 'Verified', 'Year', 'Month', 'Day', 'Hour', 'Minute', 'Second', 'Status'],
            ['001', 'Admin', '1001', '1', '2025', '01', '15', '08', '30', '00', 'IN'],
        ])
        result = self.connector._detect_columns(csv_data)
        self.assertEqual(result['pin_col'], 'EnrollNumber')
        self.assertEqual(result['date_col'], 'Year')
        self.assertEqual(result['time_col'], 'Hour')

    def test_auto_detect_generic(self):
        """Auto-detect generic columns"""
        csv_data = self._make_csv([
            ['Employee ID', 'Date', 'Time', 'Status'],
            ['1001', '2025-01-15', '08:30', 'IN'],
        ])
        result = self.connector._detect_columns(csv_data)
        self.assertEqual(result['pin_col'], 'Employee ID')

    def test_parse_csv_records(self):
        """Parse CSV records with ZKTeco format"""
        csv_data = self._make_csv([
            ['EnrollNumber', 'Year', 'Month', 'Day', 'Hour', 'Minute', 'Second', 'Status'],
            ['1001', '2025', '01', '15', '08', '30', '00', 'IN'],
            ['1001', '2025', '01', '15', '17', '00', '00', 'OUT'],
            ['1002', '2025', '01', '15', '08', '45', '00', 'IN'],
        ])
        records = self.connector._parse_csv_records(csv_data, {})
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]['pin'], '1001')
        self.assertEqual(records[0]['punch_type'], '0')  # IN

    def test_parse_status_mapping(self):
        """Status IN/OUT mapping"""
        self.assertEqual(self.connector.STATUS_IN, ['0', 'I', 'IN', 'in', 'Check In'])
        self.assertEqual(self.connector.STATUS_OUT, ['1', 'O', 'OUT', 'out', 'Check Out'])

    def test_verify_mode_mapping(self):
        """Verify mode mapping"""
        self.assertIn('1', self.connector.VERIFY_MAP)
        self.assertIn('password', self.connector.VERIFY_MAP.values())
