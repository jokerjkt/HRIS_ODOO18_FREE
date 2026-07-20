# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date, timedelta


class TestThr(TransactionCase):

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Test THR',
            'join_date': date.today() - timedelta(days=400),
        })
        self.contract = self.env['hr.contract'].create({
            'name': 'Kontrak THR',
            'employee_id': self.employee.id,
            'wage': 8_000_000,
            'state': 'open',
        })

    def test_thr_full_year(self):
        """Karyawan ≥12 bulan → THR = 1x gaji"""
        thr = self.env['hr.thr'].create({
            'employee_id': self.employee.id,
            'year': date.today().year,
            'religious_holiday': 'lebaran',
            'thr_date': date.today(),
        })
        self.assertEqual(thr.tenure_months, 13)
        self.assertAlmostEqual(thr.thr_proportion, 1.0)
        self.assertAlmostEqual(thr.thr_amount, 8_000_000, places=0)

    def test_thr_partial_year(self):
        """Karyawan 6 bulan → THR = 6/12 × gaji"""
        employee = self.env['hr.employee'].create({
            'name': 'Test THR Partial',
            'join_date': date.today() - timedelta(days=180),
        })
        self.env['hr.contract'].create({
            'name': 'Kontrak Partial',
            'employee_id': employee.id,
            'wage': 6_000_000,
            'state': 'open',
        })
        thr = self.env['hr.thr'].create({
            'employee_id': employee.id,
            'year': date.today().year,
            'religious_holiday': 'lebaran',
            'thr_date': date.today(),
        })
        self.assertGreaterEqual(thr.tenure_months, 1)
        self.assertLess(thr.tenure_months, 12)
        self.assertGreater(thr.thr_proportion, 0)
        self.assertLess(thr.thr_proportion, 1.0)

    def test_thr_new_employee(self):
        """Karyawan < 1 bulan → THR = 0"""
        employee = self.env['hr.employee'].create({
            'name': 'Test THR New',
            'join_date': date.today() - timedelta(days=5),
        })
        self.env['hr.contract'].create({
            'name': 'Kontrak New',
            'employee_id': employee.id,
            'wage': 5_000_000,
            'state': 'open',
        })
        thr = self.env['hr.thr'].create({
            'employee_id': employee.id,
            'year': date.today().year,
            'religious_holiday': 'lebaran',
            'thr_date': date.today(),
        })
        self.assertEqual(thr.tenure_months, 0)
        self.assertEqual(thr.thr_amount, 0.0)

    def test_thr_manual_override(self):
        """Manual override jika diisi"""
        thr = self.env['hr.thr'].create({
            'employee_id': self.employee.id,
            'year': date.today().year,
            'religious_holiday': 'lebaran',
            'thr_date': date.today(),
            'thr_amount_manual': 10_000_000,
        })
        self.assertEqual(thr.thr_final, 10_000_000)

    def test_thr_confirm_flow(self):
        """Test konfirmasi → paid flow"""
        thr = self.env['hr.thr'].create({
            'employee_id': self.employee.id,
            'year': date.today().year,
            'religious_holiday': 'lebaran',
            'thr_date': date.today(),
        })
        self.assertEqual(thr.state, 'draft')
        thr.action_confirm()
        self.assertEqual(thr.state, 'confirmed')
        thr.action_mark_paid()
        self.assertEqual(thr.state, 'paid')

    def test_thr_confirm_no_amount(self):
        """THR 0 tidak bisa dikonfirmasi"""
        employee = self.env['hr.employee'].create({
            'name': 'Test THR Zero',
            'join_date': date.today() - timedelta(days=5),
        })
        self.env['hr.contract'].create({
            'name': 'Kontrak Zero',
            'employee_id': employee.id,
            'wage': 5_000_000,
            'state': 'open',
        })
        thr = self.env['hr.thr'].create({
            'employee_id': employee.id,
            'year': date.today().year,
            'religious_holiday': 'lebaran',
            'thr_date': date.today(),
        })
        with self.assertRaises(UserError):
            thr.action_confirm()
