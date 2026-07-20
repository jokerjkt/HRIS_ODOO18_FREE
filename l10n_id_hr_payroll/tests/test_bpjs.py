# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from ..models.hr_bpjs import (
    BPJS_TK_RATES,
    JP_MAX_WAGE,
    BPJS_KES_EMPLOYEE_RATE,
    BPJS_KES_EMPLOYER_RATE,
    BPJS_KES_MAX_WAGE,
)


class TestBpjsRates(TransactionCase):

    def test_jht_rates(self):
        self.assertEqual(BPJS_TK_RATES['JHT']['employee'], 0.02)
        self.assertEqual(BPJS_TK_RATES['JHT']['employer'], 0.037)

    def test_jp_rates(self):
        self.assertEqual(BPJS_TK_RATES['JP']['employee'], 0.01)
        self.assertEqual(BPJS_TK_RATES['JP']['employer'], 0.02)

    def test_jkm_rate(self):
        self.assertEqual(BPJS_TK_RATES['JKM']['employer'], 0.003)

    def test_kes_rates(self):
        self.assertEqual(BPJS_KES_EMPLOYEE_RATE, 0.01)
        self.assertEqual(BPJS_KES_EMPLOYER_RATE, 0.04)

    def test_jp_max_wage(self):
        self.assertEqual(JP_MAX_WAGE, 9_077_600)

    def test_kes_max_wage(self):
        self.assertEqual(BPJS_KES_MAX_WAGE, 12_000_000)


class TestBpjsComputation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Test BPJS',
            'ptkp_status': 'TK/0',
            'bpjs_tk_jkk_class': 'I',
        })
        self.contract = self.env['hr.contract'].create({
            'name': 'Kontrak BPJS',
            'employee_id': self.employee.id,
            'wage': 10_000_000,
        })

    def test_compute_basic(self):
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
        })
        lines_dict = {
            'IDN_BASIC': 10_000_000,
            'IDN_TUNJ_TETAP': 0,
        }
        result = self.env['hr.bpjs'].compute_for_payslip(payslip, lines_dict)
        # JHT emp = 10M × 2% = 200,000
        self.assertAlmostEqual(result['IDN_BPJS_TK_JHT_EMP'], 200_000, places=0)
        # JP emp = 10M × 1% = 100,000
        self.assertAlmostEqual(result['IDN_BPJS_TK_JP_EMP'], 100_000, places=0)

    def test_jp_cap(self):
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
        })
        # Gaji besar, JP harus capped
        lines_dict = {
            'IDN_BASIC': 50_000_000,
            'IDN_TUNJ_TETAP': 0,
        }
        result = self.env['hr.bpjs'].compute_for_payslip(payslip, lines_dict)
        # JP emp = JP_MAX_WAGE × 1% = 90,776
        self.assertAlmostEqual(
            result['IDN_BPJS_TK_JP_EMP'],
            JP_MAX_WAGE * 0.01,
            places=0
        )

    def test_kes_cap(self):
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
        })
        # Gaji besar, BPJS Kes harus capped
        lines_dict = {
            'IDN_BASIC': 50_000_000,
            'IDN_TUNJ_TETAP': 0,
        }
        result = self.env['hr.bpjs'].compute_for_payslip(payslip, lines_dict)
        # Kes emp = 12M × 1% = 120,000
        self.assertAlmostEqual(
            result['IDN_BPJS_KES_EMP'],
            BPJS_KES_MAX_WAGE * 0.01,
            places=0
        )
