# -*- coding: utf-8 -*-
"""
E-Filing Wizard
===============
Wizard untuk generate SPT Tahunan dan e-Bupot.
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrEfilingWizard(models.TransientModel):
    _name = 'hr.efiling.wizard'
    _description = 'Wizard E-Filing DJP'

    year = fields.Integer(
        string='Tahun Pajak',
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Karyawan',
        help='Kosongkan untuk semua karyawan',
    )
    action_type = fields.Selection([
        ('spt', 'Generate SPT Tahunan'),
        ('ebupot', 'Generate e-Bupot'),
        ('both', 'SPT + e-Bupot'),
    ], string='Aksi', required=True, default='both')

    def action_execute(self):
        """Execute e-Filing action."""
        self.ensure_one()

        domain = [('active', '=', True)]
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))

        employees = self.env['hr.employee'].search(domain)
        if not employees:
            raise UserError('Tidak ada karyawan yang dipilih.')

        created_spts = self.env['hr.spt.tahunan']
        created_ebupots = self.env['hr.ebupot']

        for emp in employees:
            # Check if PPh 21 data exists
            pph21 = self.env['hr.pph21'].search([
                ('employee_id', '=', emp.id),
                ('period_year', '=', self.year),
            ], limit=1)
            if not pph21:
                continue

            if self.action_type in ('spt', 'both'):
                existing_spt = self.env['hr.spt.tahunan'].search([
                    ('employee_id', '=', emp.id),
                    ('year', '=', self.year),
                ], limit=1)
                if not existing_spt:
                    spt = self.env['hr.spt.tahunan'].create({
                        'employee_id': emp.id,
                        'year': self.year,
                    })
                    spt.action_compute()
                    created_spts |= spt

            if self.action_type in ('ebupot', 'both'):
                existing_ebupot = self.env['hr.ebupot'].search([
                    ('employee_id', '=', emp.id),
                    ('year', '=', self.year),
                ], limit=1)
                if not existing_ebupot:
                    ebupot = self.env['hr.ebupot'].create({
                        'employee_id': emp.id,
                        'year': self.year,
                        'form_type': '1721A1',
                    })
                    ebupot.action_compute_from_payslip()
                    ebupot.action_generate_xml()
                    created_ebupots |= ebupot

        # Return action
        if created_spts:
            return {
                'type': 'ir.actions.act_window',
                'name': f'SPT Tahunan {self.year}',
                'res_model': 'hr.spt.tahunan',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_spts.ids)],
            }
        elif created_ebupots:
            return {
                'type': 'ir.actions.act_window',
                'name': f'e-Bupot {self.year}',
                'res_model': 'hr.ebupot',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_ebupots.ids)],
            }
        else:
            raise UserError('Tidak ada data yang dihasilkan. Pastikan gaji sudah dihitung.')
