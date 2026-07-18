# -*- coding: utf-8 -*-
"""
Contract Extension
==================
Extend hr.contract untuk menambahkan field tunjangan Indonesia.
"""
from odoo import models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract'

    x_tunjangan_tetap = fields.Float(
        string='Tunjangan Tetap (Rp)',
        help='Tunjangan tetap bulanan yang menjadi komponen upah dasar BPJS',
    )
    x_tunjangan_tidak_tetap = fields.Float(
        string='Tunjangan Tidak Tetap (Rp)',
        help='Tunjangan tidak tetap/bulanan',
    )
