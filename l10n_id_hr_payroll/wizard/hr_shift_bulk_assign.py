# -*- coding: utf-8 -*-
"""
Bulk Assign Shift — Wizard untuk assign shift ke banyak karyawan sekaligus
============================================================================
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrShiftBulkAssign(models.TransientModel):
    _name = 'hr.shift.bulk.assign'
    _description = 'Wizard Bulk Assign Shift'

    rotation_id = fields.Many2one(
        'hr.shift.rotation', string='Pola Rotasi', required=True,
    )
    department_id = fields.Many2one(
        'hr.department', string='Departemen',
        help='Filter berdasarkan departemen (kosongkan untuk semua)',
    )
    employee_ids = fields.Many2many(
        'hr.employee', string='Karyawan',
        domain="[('active', '=', True)]",
    )
    date_from = fields.Date(string='Tanggal Mulai', required=True)
    date_to = fields.Date(string='Tanggal Selesai')
    overwrite_existing = fields.Boolean(
        string='Timpa Assign yang Ada',
        default=False,
        help='Jika dicentang, assign shift yang sudah ada pada periode yang overlap akan dihapus',
    )

    @api.constrains('employee_ids')
    def _check_employees(self):
        for rec in self:
            if not rec.employee_ids:
                raise ValidationError('Pilih minimal 1 karyawan!')

    def action_apply(self):
        """Apply bulk assign ke semua karyawan yang dipilih."""
        self.ensure_one()
        employee_ids = self.employee_ids.ids
        if not employee_ids:
            raise ValidationError('Pilih minimal 1 karyawan!')

        created_count = 0
        skipped_count = 0
        for emp_id in employee_ids:
            employee = self.env['hr.employee'].browse(emp_id)
            # Check overlap if not overwriting
            if not self.overwrite_existing:
                existing = self.env['hr.shift.assign'].search([
                    ('employee_id', '=', emp_id),
                    ('state', '!=', 'done'),
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', self.date_from),
                ])
                if existing and self.date_to:
                    existing_filtered = existing.filtered(
                        lambda a: a.date_from <= self.date_to
                    )
                    if existing_filtered:
                        skipped_count += 1
                        continue
            else:
                # Delete existing overlapping assignments
                existing = self.env['hr.shift.assign'].search([
                    ('employee_id', '=', emp_id),
                    ('state', '!=', 'done'),
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', self.date_from),
                ])
                if existing and self.date_to:
                    existing_filtered = existing.filtered(
                        lambda a: a.date_from <= self.date_to
                    )
                    existing_filtered.unlink()
                elif existing:
                    existing.unlink()

            # Create assignment
            assign = self.env['hr.shift.assign'].create({
                'employee_id': emp_id,
                'rotation_id': self.rotation_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
            })
            # Auto-generate daily records
            assign.action_generate_daily()
            created_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Assign Selesai',
                'message': f'{created_count} karyawan berhasil di-assign.',
                'type': 'success',
                'sticky': False,
            }
        }
