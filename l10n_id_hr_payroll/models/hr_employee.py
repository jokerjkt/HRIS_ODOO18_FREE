# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


PTKP_VALUES = {
    'TK/0': 54_000_000,
    'TK/1': 58_500_000,
    'TK/2': 63_000_000,
    'TK/3': 67_500_000,
    'K/0': 58_500_000,
    'K/1': 63_000_000,
    'K/2': 67_500_000,
    'K/3': 72_000_000,
    'K/I/0': 63_000_000,
    'K/I/1': 67_500_000,
    'K/I/2': 72_000_000,
    'K/I/3': 76_500_000,
}




class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ── Identitas Indonesia ──────────────────────────────────────────────────
    nik = fields.Char(
        string='NIK (KTP)',
        size=16,
        help='Nomor Induk Kependudukan sesuai KTP',
    )
    npwp = fields.Char(
        string='NPWP',
        size=20,
        help='Nomor Pokok Wajib Pajak. Jika kosong, tarif PPh 21 ditambah 20%.',
    )
    npwp_has = fields.Boolean(
        string='Memiliki NPWP',
        compute='_compute_npwp_has',
        store=True,
    )

    # ── PTKP ────────────────────────────────────────────────────────────────
    ptkp_status = fields.Selection(
        selection=[
            ('TK/0', 'TK/0 — Tidak Kawin, 0 tanggungan'),
            ('TK/1', 'TK/1 — Tidak Kawin, 1 tanggungan'),
            ('TK/2', 'TK/2 — Tidak Kawin, 2 tanggungan'),
            ('TK/3', 'TK/3 — Tidak Kawin, 3 tanggungan'),
            ('K/0', 'K/0 — Kawin, 0 tanggungan'),
            ('K/1', 'K/1 — Kawin, 1 tanggungan'),
            ('K/2', 'K/2 — Kawin, 2 tanggungan'),
            ('K/3', 'K/3 — Kawin, 3 tanggungan'),
            ('K/I/0', 'K/I/0 — Kawin, Penghasilan Istri Digabung, 0 tanggungan'),
            ('K/I/1', 'K/I/1 — Kawin, Penghasilan Istri Digabung, 1 tanggungan'),
            ('K/I/2', 'K/I/2 — Kawin, Penghasilan Istri Digabung, 2 tanggungan'),
            ('K/I/3', 'K/I/3 — Kawin, Penghasilan Istri Digabung, 3 tanggungan'),
        ],
        string='Status PTKP',
        default='TK/0',
        required=True,
    )
    ptkp_amount = fields.Float(
        string='Nilai PTKP (Rp/tahun)',
        compute='_compute_ptkp_amount',
        store=True,
        help='Penghasilan Tidak Kena Pajak tahunan sesuai status',
    )

    # ── BPJS Ketenagakerjaan ─────────────────────────────────────────────────
    bpjs_tk_no = fields.Char(
        string='No. Peserta BPJS TK',
        help='Nomor kepesertaan BPJS Ketenagakerjaan',
    )
    bpjs_tk_jkk_class = fields.Selection(
        selection=[
            ('I',   'Kelompok I — 0.24%'),
            ('II',  'Kelompok II — 0.54%'),
            ('III', 'Kelompok III — 0.89%'),
            ('IV',  'Kelompok IV — 1.27%'),
            ('V',   'Kelompok V — 1.74%'),
        ],
        string='Kelompok Risiko JKK',
        default='I',
        help='Kelompok risiko pekerjaan untuk iuran Jaminan Kecelakaan Kerja',
    )
    bpjs_tk_jkk_rate = fields.Float(
        string='Rate JKK (%)',
        compute='_compute_bpjs_tk_jkk_rate',
        store=True,
    )

    # ── BPJS Kesehatan ───────────────────────────────────────────────────────
    bpjs_kes_no = fields.Char(
        string='No. Peserta BPJS Kesehatan',
    )
    bpjs_kes_class = fields.Selection(
        selection=[
            ('1', 'Kelas 1'),
            ('2', 'Kelas 2'),
            ('3', 'Kelas 3'),
        ],
        string='Kelas BPJS Kesehatan',
        default='1',
    )

    # ── Tanggal Bergabung (untuk THR) ────────────────────────────────────────
    join_date = fields.Date(
        string='Tanggal Bergabung',
        help='Digunakan untuk menghitung masa kerja dan THR proporsional',
    )
    tenure_months = fields.Integer(
        string='Masa Kerja (Bulan)',
        compute='_compute_tenure_months',
        store=False,
    )

    # ── Tipe Karyawan ────────────────────────────────────────────────────────
    employee_contract_type = fields.Selection(
        selection=[
            ('permanent', 'Karyawan Tetap (A1)'),
            ('contract',  'Karyawan Tidak Tetap (A2)'),
            ('daily',     'Karyawan Harian Lepas'),
        ],
        string='Tipe Kontrak',
        default='permanent',
        help='Menentukan formulir Bukti Potong yang digunakan (1721-A1 atau A2)',
    )

    # ── Data Bank ────────────────────────────────────────────────────────────
    bank_name = fields.Char(
        string='Nama Bank',
        help='Nama bank untuk transfer gaji',
    )
    bank_branch = fields.Char(
        string='Cabang Bank',
        help='Cabang bank tempat rekening dibuka',
    )
    bank_account_number = fields.Char(
        string='Nomor Rekening',
        help='Nomor rekening bank untuk transfer gaji',
    )
    bank_account_name = fields.Char(
        string='Atas Nama Rekening',
        help='Nama pemegang rekening sesuai buku tabungan',
    )

    # ────────────────────────────────────────────────────────────────────────
    # Compute Methods
    # ────────────────────────────────────────────────────────────────────────

    @api.depends('npwp')
    def _compute_npwp_has(self):
        for emp in self:
            emp.npwp_has = bool(emp.npwp and emp.npwp.strip())

    @api.depends('ptkp_status')
    def _compute_ptkp_amount(self):
        for emp in self:
            emp.ptkp_amount = PTKP_VALUES.get(emp.ptkp_status, 54_000_000)

    @api.depends('bpjs_tk_jkk_class')
    def _compute_bpjs_tk_jkk_rate(self):
        for emp in self:
            if emp.bpjs_tk_jkk_class:
                rate_rec = self.env['hr.bpjs.rate'].search(
                    [('code', '=', emp.bpjs_tk_jkk_class)], limit=1
                )
                emp.bpjs_tk_jkk_rate = rate_rec.jkk_rate if rate_rec else 0.0024
            else:
                emp.bpjs_tk_jkk_rate = 0.0024

    @api.depends('join_date')
    def _compute_tenure_months(self):
        today = fields.Date.today()
        for emp in self:
            if emp.join_date:
                delta = (today.year - emp.join_date.year) * 12 + (today.month - emp.join_date.month)
                emp.tenure_months = max(delta, 0)
            else:
                emp.tenure_months = 0

    # ────────────────────────────────────────────────────────────────────────
    # Constraints
    # ────────────────────────────────────────────────────────────────────────

    @api.constrains('nik')
    def _check_nik(self):
        for emp in self:
            if emp.nik and (not emp.nik.isdigit() or len(emp.nik) != 16):
                raise ValidationError('NIK harus berupa 16 digit angka.')

    @api.constrains('npwp')
    def _check_npwp(self):
        for emp in self:
            if emp.npwp:
                digits = ''.join(filter(str.isdigit, emp.npwp))
                if len(digits) not in (15, 16):
                    raise ValidationError('NPWP harus berisi 15 atau 16 digit angka.')
