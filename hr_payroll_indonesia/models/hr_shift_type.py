# -*- coding: utf-8 -*-
"""
Shift Type — Definisi tipe shift (Pagi, Siang, Malam, Libur)
=============================================================
"""
from odoo import models, fields, api


class HrShiftType(models.Model):
    _name = 'hr.shift.type'
    _description = 'Tipe Shift'
    _order = 'hour_from, name'

    name = fields.Char(string='Nama Shift', required=True, translate=True)
    code = fields.Char(string='Kode', required=True, size=3)
    hour_from = fields.Float(string='Jam Mulai', required=True)
    hour_to = fields.Float(string='Jam Selesai', required=True)
    duration = fields.Float(string='Durasi (jam)', compute='_compute_duration', store=True)
    color = fields.Integer(string='Warna', default=0)
    is_rest = fields.Boolean(string='Hari Libur', default=False)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Kode shift harus unik!'),
    ]

    @api.depends('hour_from', 'hour_to')
    def _compute_duration(self):
        for rec in self:
            if rec.hour_to >= rec.hour_from:
                rec.duration = rec.hour_to - rec.hour_from
            else:
                rec.duration = (24 - rec.hour_from) + rec.hour_to
