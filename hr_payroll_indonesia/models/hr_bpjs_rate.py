# -*- coding: utf-8 -*-
"""
BPJS Rate Configuration
========================
Konfigurasi tarif BPJS Ketenagakerjaan per kelompok risiko.
Referensi: PP No. 44 Tahun 2015, PP No. 2 Tahun 2022
"""
from odoo import models, fields


class HrBpjsRate(models.Model):
    _name = 'hr.bpjs.rate'
    _description = 'Konfigurasi Tarif BPJS'
    _order = 'code'

    name = fields.Char(
        string='Nama Kelompok',
        required=True,
    )
    code = fields.Selection(
        selection=[
            ('I',   'Kelompok I — Sangat Rendah'),
            ('II',  'Kelompok II — Rendah'),
            ('III', 'Kelompok III — Menengah'),
            ('IV',  'Kelompok IV — Tinggi'),
            ('V',   'Kelompok V — Sangat Tinggi'),
        ],
        string='Kode',
        required=True,
    )
    jkk_rate = fields.Float(
        string='Tarif JKK (%)',
        required=True,
        default=0.24,
        help='Persentase iuran Jaminan Kecelakaan Kerja',
    )
    jkm_rate = fields.Float(
        string='Tarif JKM (%)',
        required=True,
        default=0.30,
        help='Persentase iuran Jaminan Kematian',
    )
    jht_rate_employer = fields.Float(
        string='JHT Perusahaan (%)',
        required=True,
        default=3.70,
        help='Persentase iuran JHT pihak perusahaan',
    )
    jht_rate_employee = fields.Float(
        string='JHT Karyawan (%)',
        required=True,
        default=2.00,
        help='Persentase iuran JHT pihak karyawan',
    )
    jp_rate_employer = fields.Float(
        string='JP Perusahaan (%)',
        required=True,
        default=2.00,
        help='Persentase iuran JP pihak perusahaan',
    )
    jp_rate_employee = fields.Float(
        string='JP Karyawan (%)',
        required=True,
        default=1.00,
        help='Persentase iuran JP pihak karyawan',
    )
    description = fields.Text(
        string='Deskripsi',
        help='Contoh jenis industri untuk kelompok risiko ini',
    )
