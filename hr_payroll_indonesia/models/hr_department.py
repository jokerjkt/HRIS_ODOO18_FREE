# -*- coding: utf-8 -*-
"""
Department Extension
===================
Extend hr.department untuk menambahkan kode divisi.
Kode digunakan dalam penomoran slip gaji.
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    code = fields.Char(
        string='Kode Divisi',
        size=5,
        help='Kode singkat divisi (contoh: SALES, MGMT, HRD). '
             'Digunakan dalam nomor transaksi slip gaji.',
    )

    @api.constrains('code')
    def _check_code(self):
        for dept in self:
            if dept.code:
                if len(dept.code) > 5:
                    raise ValidationError('Kode divisi maksimal 5 karakter.')
                # Check uniqueness
                existing = self.search([
                    ('code', '=', dept.code),
                    ('id', '!=', dept.id),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        f'Kode divisi "{dept.code}" sudah digunakan oleh '
                        f'departemen {existing.name}.'
                    )
