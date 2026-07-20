# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from ..models.hr_pph21 import (
    hitung_pph21_progresif,
    PTKP_TABLE,
    BIAYA_JABATAN_RATE,
    BIAYA_JABATAN_MAX,
    TANPA_NPWP_SURCHARGE,
)


class TestPPh21Progresif(TransactionCase):

    def test_pph21_zero(self):
        """PKP 0 = PPh 0"""
        self.assertEqual(hitung_pph21_progresif(0), 0.0)

    def test_pph21_5_percent(self):
        """PKP ≤ 60 juta = tarif 5%"""
        result = hitung_pph21_progresif(60_000_000)
        self.assertAlmostEqual(result, 3_000_000, places=0)

    def test_pph21_15_percent(self):
        """PKP 250 juta = 5% × 60j + 15% × 190j"""
        result = hitung_pph21_progresif(250_000_000)
        expected = 60_000_000 * 0.05 + 190_000_000 * 0.15
        self.assertAlmostEqual(result, expected, places=0)

    def test_pph21_25_percent(self):
        """PKP 500 juta"""
        result = hitung_pph21_progresif(500_000_000)
        expected = 60_000_000 * 0.05 + 190_000_000 * 0.15 + 250_000_000 * 0.25
        self.assertAlmostEqual(result, expected, places=0)

    def test_pph21_30_percent(self):
        """PKP 1 miliar"""
        result = hitung_pph21_progresif(1_000_000_000)
        expected = (60_000_000 * 0.05 + 190_000_000 * 0.15 +
                    250_000_000 * 0.25 + 500_000_000 * 0.30)
        self.assertAlmostEqual(result, expected, places=0)

    def test_pph21_35_percent(self):
        """PKP 6 miliar = max tier"""
        result = hitung_pph21_progresif(6_000_000_000)
        expected = (60_000_000 * 0.05 + 190_000_000 * 0.15 +
                    250_000_000 * 0.25 + 5_000_000_000 * 0.30 +
                    1_000_000_000 * 0.35)
        self.assertAlmostEqual(result, expected, places=0)

    def test_ptkp_table_completeness(self):
        """Semua status PTKP punya nilai"""
        expected_keys = ['TK/0', 'TK/1', 'TK/2', 'TK/3',
                         'K/0', 'K/1', 'K/2', 'K/3',
                         'K/I/0', 'K/I/1', 'K/I/2', 'K/I/3']
        for key in expected_keys:
            self.assertIn(key, PTKP_TABLE)
            self.assertGreater(PTKP_TABLE[key], 0)

    def test_biaya_jabatan_max(self):
        """Biaya jabatan maksimal Rp 6 juta/tahun"""
        self.assertEqual(BIAYA_JABATAN_MAX, 6_000_000)

    def test_biaya_jabatan_rate(self):
        """Rate biaya jabatan 5%"""
        self.assertEqual(BIAYA_JABATAN_RATE, 0.05)

    def test_surcharge_rate(self):
        """Surcharge tanpa NPWP 20%"""
        self.assertEqual(TANPA_NPWP_SURCHARGE, 0.20)


class TestPPh21Model(TransactionCase):

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Karyawan PPh21',
            'ptkp_status': 'TK/0',
        })
        self.contract = self.env['hr.contract'].create({
            'name': 'Kontrak Test',
            'employee_id': self.employee.id,
            'wage': 10_000_000,
        })

    def test_compute_for_payslip_basic(self):
        """PPh 21 bisa dihitung untuk payslip sederhana"""
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
        })
        lines_dict = {
            'IDN_BASIC': 10_000_000,
            'IDN_TUNJ_TETAP': 2_000_000,
            'IDN_TUNJ_TIDAK_TETAP': 0,
            'IDN_BONUS': 0,
            'IDN_THR': 0,
            'IDN_OVERTIME': 0,
            'IDN_BPJS_TK_JHT_EMP': 0,
            'IDN_BPJS_TK_JP_EMP': 0,
        }
        pph21 = self.env['hr.pph21'].compute_for_payslip(payslip, lines_dict)
        self.assertGreaterEqual(pph21, 0)
