# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestEmployee(TransactionCase):

    def test_employee_ptkp_default(self):
        """Default PTKP = TK/0"""
        emp = self.env['hr.employee'].create({'name': 'Test Default'})
        self.assertEqual(emp.ptkp_status, 'TK/0')

    def test_employee_ptkp_values(self):
        """Semua status PTKP valid"""
        valid = ['TK/0', 'TK/1', 'TK/2', 'TK/3',
                 'K/0', 'K/1', 'K/2', 'K/3',
                 'K/I/0', 'K/I/1', 'K/I/2', 'K/I/3']
        for status in valid:
            emp = self.env['hr.employee'].create({
                'name': f'Test {status}',
                'ptkp_status': status,
            })
            self.assertEqual(emp.ptkp_status, status)

    def test_employee_ptkp_amount_computation(self):
        """PTKP amount = nilai dari PTKP_VALUES"""
        emp = self.env['hr.employee'].create({
            'name': 'Test PTKP Amount',
            'ptkp_status': 'K/1',
        })
        self.assertEqual(emp.ptkp_amount, 63_000_000)

    def test_employee_npwp_has(self):
        """npwp_has = True jika ada NPWP"""
        emp = self.env['hr.employee'].create({
            'name': 'Test NPWP',
            'npwp': '123456789012345',
        })
        self.assertTrue(emp.npwp_has)

    def test_employee_npwp_empty(self):
        """npwp_has = False jika NPWP kosong"""
        emp = self.env['hr.employee'].create({
            'name': 'Test No NPWP',
        })
        self.assertFalse(emp.npwp_has)

    def test_employee_bank_info(self):
        """Bank info bisa disimpan"""
        emp = self.env['hr.employee'].create({
            'name': 'Test Bank',
            'bank_name': 'Bank Central Asia (BCA)',
            'bank_branch': 'KCP Sudirman',
            'bank_account_number': '1234567890',
            'bank_account_name': 'Test Bank',
        })
        self.assertEqual(emp.bank_name, 'Bank Central Asia (BCA)')
        self.assertEqual(emp.bank_account_number, '1234567890')

    def test_employee_contract_type(self):
        """Jenis kontrak tersimpan"""
        emp = self.env['hr.employee'].create({
            'name': 'Test Contract Type',
            'employee_contract_type': 'permanent',
        })
        self.assertEqual(emp.employee_contract_type, 'permanent')
