# -*- coding: utf-8 -*-
"""
PPh 21 Computation Engine
=========================
Menghitung Pajak Penghasilan Pasal 21 sesuai regulasi Indonesia terbaru.

Referensi:
- UU HPP No. 7 Tahun 2021
- PMK No. 168/PMK.010/2023 (efektif Jan 2024)
- Tarif PTKP sesuai PMK No. 101/PMK.010/2016
"""
from odoo import models, fields, api
from .hr_employee import PTKP_VALUES


# ── Tarif Progresif PPh 21 (Pasal 17) ───────────────────────────────────────
# Format: (batas_atas_penghasilan_kena_pajak, tarif)
# Penghasilan dihitung per tahun
TARIF_PPH21 = [
    (60_000_000,        0.05),   # 0 – 60 juta          → 5%
    (250_000_000,       0.15),   # 60 juta – 250 juta   → 15%
    (500_000_000,       0.25),   # 250 juta – 500 juta  → 25%
    (5_000_000_000,     0.30),   # 500 juta – 5 miliar  → 30%
    (float('inf'),      0.35),   # > 5 miliar           → 35%
]

PTKP_TABLE = PTKP_VALUES

# ── Biaya Jabatan (maks per tahun) ──────────────────────────────────────────
BIAYA_JABATAN_RATE = 0.05
BIAYA_JABATAN_MAX  = 6_000_000   # Rp 6.000.000 / tahun

# ── Penambahan tarif jika tidak punya NPWP ──────────────────────────────────
TANPA_NPWP_SURCHARGE = 0.20   # +20% dari PPh yang terutang


def hitung_pph21_progresif(pkp_tahunan: float) -> float:
    """
    Hitung PPh 21 tahunan menggunakan tarif progresif berlapis (Pasal 17).

    :param pkp_tahunan: Penghasilan Kena Pajak setahun (Rp)
    :return: PPh 21 terutang setahun (Rp)
    """
    pph = 0.0
    batas_bawah = 0.0
    for batas_atas, tarif in TARIF_PPH21:
        if pkp_tahunan <= batas_bawah:
            break
        lapisan = min(pkp_tahunan, batas_atas) - batas_bawah
        pph += lapisan * tarif
        batas_bawah = batas_atas
    return pph


class HrPph21(models.Model):
    """
    Model bantu untuk menyimpan rincian kalkulasi PPh 21 per slip gaji.
    Dihitung otomatis saat payslip dikonfirmasi.
    """
    _name = 'hr.pph21'
    _description = 'Rincian Kalkulasi PPh 21'
    _order = 'payslip_id desc'

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Slip Gaji',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        related='payslip_id.employee_id',
        store=True,
    )
    period_month = fields.Integer(
        string='Bulan',
        compute='_compute_period',
        store=True,
    )
    period_year = fields.Integer(
        string='Tahun',
        compute='_compute_period',
        store=True,
    )

    # ── Input komponen ────────────────────────────────────────────────────────
    gaji_pokok        = fields.Float('Gaji Pokok (Rp)')
    tunjangan_tetap   = fields.Float('Tunjangan Tetap (Rp)')
    tunjangan_lain    = fields.Float('Tunjangan Tidak Tetap (Rp)')
    bonus_thr         = fields.Float('Bonus / THR (Rp)')
    penghasilan_bruto = fields.Float('Penghasilan Bruto Bulanan (Rp)', store=True)
    penghasilan_bruto_tahunan = fields.Float('Penghasilan Bruto Setahun (Rp)')

    # ── Pengurang ─────────────────────────────────────────────────────────────
    biaya_jabatan     = fields.Float('Biaya Jabatan (Rp)')
    iuran_pensiun_emp = fields.Float('Iuran Pensiun Karyawan (Rp)')
    bpjs_tk_jht_emp   = fields.Float('JHT Karyawan (Rp)')
    bpjs_tk_jp_emp    = fields.Float('JP Karyawan (Rp)')
    total_pengurang   = fields.Float('Total Pengurang (Rp)')

    # ── PKP ───────────────────────────────────────────────────────────────────
    ptkp_status       = fields.Char('Status PTKP')
    ptkp_amount       = fields.Float('PTKP (Rp/tahun)')
    penghasilan_neto  = fields.Float('Penghasilan Neto Setahun (Rp)')
    pkp_tahunan       = fields.Float('PKP Setahun (Rp)')

    # ── PPh 21 ────────────────────────────────────────────────────────────────
    pph21_tahunan     = fields.Float('PPh 21 Setahun (Rp)')
    pph21_bulanan     = fields.Float('PPh 21 Bulanan (Rp)')
    pph21_surcharge   = fields.Float('Surcharge Tanpa NPWP (Rp)')
    pph21_final       = fields.Float('PPh 21 Terutang Bulan Ini (Rp)')
    is_december_adj   = fields.Boolean('Penyesuaian Desember')
    npwp_has          = fields.Boolean('Memiliki NPWP')
    note              = fields.Text('Keterangan')

    # ────────────────────────────────────────────────────────────────────────
    # Business Logic
    # ────────────────────────────────────────────────────────────────────────

    @api.depends('payslip_id.date_from')
    def _compute_period(self):
        for rec in self:
            if rec.payslip_id and rec.payslip_id.date_from:
                rec.period_month = rec.payslip_id.date_from.month
                rec.period_year = rec.payslip_id.date_from.year
            else:
                rec.period_month = 0
                rec.period_year = 0

    @api.model
    def compute_for_payslip(self, payslip, lines_dict):
        """
        Entry point utama — dipanggil dari hr_payslip saat kalkulasi gaji.

        :param payslip: record hr.payslip
        :param lines_dict: dict {code: amount} dari payslip lines
        :return: float — jumlah PPh 21 yang harus dipotong bulan ini
        """
        emp = payslip.employee_id
        date_from = payslip.date_from

        # 1. Kumpulkan komponen penghasilan
        gaji_pokok      = lines_dict.get('IDN_BASIC', 0.0)
        tunj_tetap      = lines_dict.get('IDN_TUNJ_TETAP', 0.0)
        tunj_lain       = lines_dict.get('IDN_TUNJ_TIDAK_TETAP', 0.0)
        bonus_thr       = lines_dict.get('IDN_BONUS', 0.0) + lines_dict.get('IDN_THR', 0.0)
        overtime        = lines_dict.get('IDN_OVERTIME', 0.0)

        penghasilan_bruto = gaji_pokok + tunj_tetap + tunj_lain + bonus_thr + overtime

        # 2. Anualisasi (dikali 12 bulan)
        penghasilan_bruto_tahunan = penghasilan_bruto * 12

        # 3. Biaya Jabatan (5%, maks 6 juta/tahun)
        biaya_jabatan = min(penghasilan_bruto_tahunan * BIAYA_JABATAN_RATE, BIAYA_JABATAN_MAX)

        # 4. Iuran BPJS (pengurang)
        jht_emp = lines_dict.get('IDN_BPJS_TK_JHT_EMP', 0.0) * 12
        jp_emp  = lines_dict.get('IDN_BPJS_TK_JP_EMP', 0.0) * 12

        total_pengurang = biaya_jabatan + jht_emp + jp_emp

        # 5. Penghasilan Neto & PKP
        ptkp_status = emp.ptkp_status or 'TK/0'
        ptkp_amount = PTKP_TABLE.get(ptkp_status, 54_000_000)
        penghasilan_neto = penghasilan_bruto_tahunan - total_pengurang
        pkp_tahunan = max(penghasilan_neto - ptkp_amount, 0)

        # Pembulatan ke ribuan ke bawah (sesuai PMK)
        pkp_tahunan = (pkp_tahunan // 1000) * 1000

        # 6. Hitung PPh 21 progresif
        pph21_tahunan = hitung_pph21_progresif(pkp_tahunan)

        # 7. Surcharge jika tidak ada NPWP
        surcharge = 0.0
        if not emp.npwp_has:
            surcharge = pph21_tahunan * TANPA_NPWP_SURCHARGE
            pph21_tahunan += surcharge

        # 8. PPh bulanan
        pph21_bulanan = pph21_tahunan / 12

        # 9. Penyesuaian bulan Desember
        is_december = date_from.month == 12
        pph21_final = pph21_bulanan  # TODO: kurangi akumulasi bulan Jan-Nov di Desember

        # 10. Simpan rincian
        existing = self.search([('payslip_id', '=', payslip.id)], limit=1)
        vals = {
            'payslip_id':               payslip.id,
            'gaji_pokok':               gaji_pokok,
            'tunjangan_tetap':          tunj_tetap,
            'tunjangan_lain':           tunj_lain,
            'bonus_thr':                bonus_thr,
            'penghasilan_bruto':        penghasilan_bruto,
            'penghasilan_bruto_tahunan': penghasilan_bruto_tahunan,
            'biaya_jabatan':            biaya_jabatan / 12,
            'bpjs_tk_jht_emp':          jht_emp / 12,
            'bpjs_tk_jp_emp':           jp_emp / 12,
            'total_pengurang':          total_pengurang / 12,
            'ptkp_status':              ptkp_status,
            'ptkp_amount':              ptkp_amount,
            'penghasilan_neto':         penghasilan_neto,
            'pkp_tahunan':              pkp_tahunan,
            'pph21_tahunan':            pph21_tahunan,
            'pph21_bulanan':            pph21_bulanan,
            'pph21_surcharge':          surcharge / 12,
            'pph21_final':              pph21_final,
            'is_december_adj':          is_december,
            'npwp_has':                 emp.npwp_has,
            'note':                     f'Dihitung otomatis — {date_from.strftime("%B %Y")}',
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)

        return pph21_final
