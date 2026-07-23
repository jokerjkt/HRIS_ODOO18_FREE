# -*- coding: utf-8 -*-
"""
BPJS Computation Engine
========================
Menghitung iuran BPJS Ketenagakerjaan dan BPJS Kesehatan.

Referensi:
- PP No. 44 Tahun 2015 (JKK, JKM)
- PP No. 46 Tahun 2015 (JHT)
- PP No. 45 Tahun 2015 (JP)
- Perpres No. 75 Tahun 2019 (BPJS Kesehatan)
- PerBPJS No. 6 Tahun 2023 (update rate BPJS Kesehatan)
"""
from odoo import models, fields, api

# ── Rate BPJS Ketenagakerjaan ────────────────────────────────────────────────
BPJS_TK_RATES = {
    'JHT': {'employee': 0.02,  'employer': 0.037},   # Jaminan Hari Tua
    'JP':  {'employee': 0.01,  'employer': 0.02},    # Jaminan Pensiun
    'JKM': {'employee': 0.0,   'employer': 0.003},   # Jaminan Kematian
}

# Batas upah JP per Juli 2024 (diupdate tiap tahun oleh pemerintah)
JP_MAX_WAGE = 9_077_600   # Rp 9.077.600/bulan



# ── Rate BPJS Kesehatan ──────────────────────────────────────────────────────
BPJS_KES_EMPLOYEE_RATE = 0.01   # 1% ditanggung karyawan
BPJS_KES_EMPLOYER_RATE = 0.04   # 4% ditanggung perusahaan
BPJS_KES_MAX_WAGE      = 12_000_000  # Rp 12.000.000/bulan


class HrBpjs(models.Model):
    """
    Model bantu untuk menyimpan rincian iuran BPJS per slip gaji.
    """
    _name = 'hr.bpjs'
    _description = 'Rincian Iuran BPJS'
    _order = 'payslip_id desc'

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Slip Gaji',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        related='payslip_id.employee_id',
        store=True,
    )
    upah_dasar = fields.Float('Upah Dasar Penghitungan (Rp)')

    # ── BPJS Ketenagakerjaan — Karyawan ──────────────────────────────────────
    jht_emp  = fields.Float('JHT Karyawan (2%) Rp')
    jp_emp   = fields.Float('JP Karyawan (1%) Rp')
    total_tk_emp = fields.Float('Total Potongan TK Karyawan (Rp)')

    # ── BPJS Ketenagakerjaan — Perusahaan ────────────────────────────────────
    jkk_comp = fields.Float('JKK Perusahaan (Rp)')
    jkm_comp = fields.Float('JKM Perusahaan (0.3%) Rp')
    jht_comp = fields.Float('JHT Perusahaan (3.7%) Rp')
    jp_comp  = fields.Float('JP Perusahaan (2%) Rp')
    total_tk_comp = fields.Float('Total Kontribusi TK Perusahaan (Rp)')

    # ── BPJS Kesehatan ────────────────────────────────────────────────────────
    bpjs_kes_emp  = fields.Float('BPJS Kes Karyawan (1%) Rp')
    bpjs_kes_comp = fields.Float('BPJS Kes Perusahaan (4%) Rp')
    upah_kes_base = fields.Float('Upah Dasar BPJS Kes (capped Rp 12jt)')

    # ── Total ─────────────────────────────────────────────────────────────────
    total_potongan_karyawan = fields.Float('Total Potongan Karyawan (Rp)')
    total_kontribusi_perusahaan = fields.Float('Total Kontribusi Perusahaan (Rp)')
    note = fields.Text('Keterangan')

    # ────────────────────────────────────────────────────────────────────────
    # Business Logic
    # ────────────────────────────────────────────────────────────────────────

    @api.model
    def compute_for_payslip(self, payslip, lines_dict):
        """
        Entry point utama — hitung semua komponen BPJS untuk satu payslip.

        :param payslip: record hr.payslip
        :param lines_dict: dict {code: amount}
        :return: dict berisi semua nilai BPJS (untuk dipakai salary rules)
        """
        emp = payslip.employee_id

        # Upah dasar = gaji pokok + tunjangan tetap
        upah_dasar = (
            lines_dict.get('IDN_BASIC', 0.0)
            + lines_dict.get('IDN_TUNJ_TETAP', 0.0)
        )

        # ── BPJS Ketenagakerjaan ──────────────────────────────────────────
        # JHT
        jht_emp  = upah_dasar * BPJS_TK_RATES['JHT']['employee']
        jht_comp = upah_dasar * BPJS_TK_RATES['JHT']['employer']

        # JP — upah dibatasi JP_MAX_WAGE
        upah_jp = min(upah_dasar, JP_MAX_WAGE)
        jp_emp   = upah_jp * BPJS_TK_RATES['JP']['employee']
        jp_comp  = upah_jp * BPJS_TK_RATES['JP']['employer']

        # JKK — rate sesuai kelompok risiko karyawan
        jkk_class = emp.bpjs_tk_jkk_class or 'I'
        rate_rec = self.env['hr.bpjs.rate'].search(
            [('code', '=', jkk_class)], limit=1
        )
        jkk_rate = rate_rec.jkk_rate if rate_rec else 0.0024
        jkk_comp = upah_dasar * jkk_rate

        # JKM
        jkm_comp = upah_dasar * BPJS_TK_RATES['JKM']['employer']

        total_tk_emp  = jht_emp + jp_emp
        total_tk_comp = jkk_comp + jkm_comp + jht_comp + jp_comp

        # ── BPJS Kesehatan ────────────────────────────────────────────────
        upah_kes = min(upah_dasar, BPJS_KES_MAX_WAGE)
        bpjs_kes_emp  = upah_kes * BPJS_KES_EMPLOYEE_RATE
        bpjs_kes_comp = upah_kes * BPJS_KES_EMPLOYER_RATE

        total_potongan     = total_tk_emp + bpjs_kes_emp
        total_kontribusi   = total_tk_comp + bpjs_kes_comp

        # Simpan rincian
        existing = self.search([('payslip_id', '=', payslip.id)], limit=1)
        vals = {
            'payslip_id':               payslip.id,
            'upah_dasar':               upah_dasar,
            'jht_emp':                  jht_emp,
            'jp_emp':                   jp_emp,
            'total_tk_emp':             total_tk_emp,
            'jkk_comp':                 jkk_comp,
            'jkm_comp':                 jkm_comp,
            'jht_comp':                 jht_comp,
            'jp_comp':                  jp_comp,
            'total_tk_comp':            total_tk_comp,
            'bpjs_kes_emp':             bpjs_kes_emp,
            'bpjs_kes_comp':            bpjs_kes_comp,
            'upah_kes_base':            upah_kes,
            'total_potongan_karyawan':  total_potongan,
            'total_kontribusi_perusahaan': total_kontribusi,
            'note': f'Upah dasar: {upah_dasar:,.0f} | JP cap: {upah_jp:,.0f} | Kes cap: {upah_kes:,.0f}',
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)

        return {
            'IDN_BPJS_TK_JHT_EMP':  jht_emp,
            'IDN_BPJS_TK_JP_EMP':   jp_emp,
            'IDN_BPJS_TK_JKK':      jkk_comp,
            'IDN_BPJS_TK_JKM':      jkm_comp,
            'IDN_BPJS_TK_JHT_COMP': jht_comp,
            'IDN_BPJS_TK_JP_COMP':  jp_comp,
            'IDN_BPJS_KES_EMP':     bpjs_kes_emp,
            'IDN_BPJS_KES_COMP':    bpjs_kes_comp,
        }
