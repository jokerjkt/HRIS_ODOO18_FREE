# -*- coding: utf-8 -*-
"""
PPh 21 Computation Engine
=========================
Menghitung Pajak Penghasilan Pasal 21 sesuai regulasi Indonesia terbaru.

Fitur:
- Tarif progresif berlapis (Pasal 17)
- THR & Bonus dihitung PPh 21-nya secara terpisah (tidak dianualisasi)
- Rekonsiliasi bulan Desember (akumulasi Jan-Nov dikurangi)

Referensi:
- UU HPP No. 7 Tahun 2021
- PMK No. 168/PMK.010/2023 (efektif Jan 2024)
- PMK No. 101/PMK.010/2016 (PTKP)
"""
from odoo import models, fields, api
from .hr_employee import PTKP_VALUES


# ── Tarif Progresif PPh 21 (Pasal 17) ───────────────────────────────────────
TARIF_PPH21 = [
    (60_000_000,        0.05),
    (250_000_000,       0.15),
    (500_000_000,       0.25),
    (5_000_000_000,     0.30),
    (float('inf'),      0.35),
]

PTKP_TABLE = PTKP_VALUES

BIAYA_JABATAN_RATE = 0.05
BIAYA_JABATAN_MAX  = 6_000_000

TANPA_NPWP_SURCHARGE = 0.20


def hitung_pph21_progresif(pkp_tahunan):
    """Hitung PPh 21 tahunan menggunakan tarif progresif berlapis."""
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
    _name = 'hr.pph21'
    _description = 'Rincian Kalkulasi PPh 21'
    _order = 'payslip_id desc'

    payslip_id = fields.Many2one(
        'hr.payslip', string='Slip Gaji',
        required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Karyawan',
        related='payslip_id.employee_id', store=True,
    )
    period_month = fields.Integer(string='Bulan', compute='_compute_period', store=True)
    period_year = fields.Integer(string='Tahun', compute='_compute_period', store=True)

    # ── Gaji reguler (tanpa THR/bonus) ───────────────────────────────────────
    gaji_pokok        = fields.Float('Gaji Pokok (Rp)')
    tunjangan_tetap   = fields.Float('Tunjangan Tetap (Rp)')
    tunjangan_lain    = fields.Float('Tunjangan Tidak Tetap (Rp)')
    overtime          = fields.Float('Lembur (Rp)')
    penghasilan_bruto_reguler = fields.Float('Bruto Reguler Bulanan (Rp)')
    penghasilan_bruto_reguler_tahunan = fields.Float('Bruto Reguler Setahun (Rp)')

    # ── THR & Bonus (terpisah) ───────────────────────────────────────────────
    bonus_thr         = fields.Float('Bonus / THR (Rp)')
    pph21_bonus_thr   = fields.Float('PPh 21 atas Bonus/THR (Rp)')

    # ── Penghasilan bruto total ───────────────────────────────────────────────
    penghasilan_bruto = fields.Float('Penghasilan Bruto Bulanan (Rp)')
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

    # ── PPh 21 gaji reguler ───────────────────────────────────────────────────
    pph21_tahunan     = fields.Float('PPh 21 Reguler Setahun (Rp)')
    pph21_bulanan     = fields.Float('PPh 21 Reguler Bulanan (Rp)')
    pph21_surcharge   = fields.Float('Surcharge Tanpa NPWP (Rp)')

    # ── PPh 21 final ─────────────────────────────────────────────────────────
    pph21_final       = fields.Float('PPh 21 Terutang Bulan Ini (Rp)')
    pph21_akumulasi_jan_nov = fields.Float('Akumulasi PPh 21 Jan-Nov (Rp)')
    is_december_adj   = fields.Boolean('Penyesuaian Desember')
    npwp_has          = fields.Boolean('Memiliki NPWP')
    note              = fields.Text('Keterangan')

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
    def _get_akumulasi_pph21(self, employee_id, year):
        """Hitung total PPh 21 reguler yang sudah dipotong dari Jan-Nov."""
        domain = [
            ('employee_id', '=', employee_id),
            ('period_year', '=', year),
            ('period_month', '>=', 1),
            ('period_month', '<=', 11),
            ('is_december_adj', '=', False),
        ]
        existing = self.search(domain)
        return sum(existing.mapped('pph21_bulanan'))

    @api.model
    def _hitung_pph21_bonus_thr(self, bonus_thr_amount, emp, ptkp_amount, pkp_gaji_tahunan):
        """
        Hitung PPh 21 untuk bonus/THR secara terpisah.
        Menggunakan tarif progresif berdasarkan PKP gabungan (gaji + bonus).

        :param bonus_thr_amount: jumlah bonus/THR
        :param emp: employee record
        :param ptkp_amount: nilai PTKP
        :param pkp_gaji_tahunan: PKP dari gaji reguler saja (sebelum bonus)
        :return: PPh 21 atas bonus/THR
        """
        if bonus_thr_amount <= 0:
            return 0.0

        # PKP dari gaji reguler saja (tanpa bonus)
        pph21_gaji = hitung_pph21_progresif(pkp_gaji_tahunan)

        # PKP gabungan (gaji + bonus)
        pkp_gabungan = pkp_gaji_tahunan + bonus_thr_amount
        pph21_gabungan = hitung_pph21_progresif(pkp_gabungan)

        # PPh 21 atas bonus = selisih
        pph21_bonus = pph21_gabungan - pph21_gaji
        return max(pph21_bonus, 0.0)

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

        # ── 1. Kumpulkan komponen penghasilan ──────────────────────────────
        gaji_pokok  = lines_dict.get('IDN_BASIC', 0.0)
        tunj_tetap  = lines_dict.get('IDN_TUNJ_TETAP', 0.0)
        tunj_lain   = lines_dict.get('IDN_TUNJ_TIDAK_TETAP', 0.0)
        overtime    = lines_dict.get('IDN_OVERTIME', 0.0)
        bonus_thr   = lines_dict.get('IDN_BONUS', 0.0) + lines_dict.get('IDN_THR', 0.0)

        # Gaji reguler (tanpa THR/bonus)
        bruto_reguler_bulanan = gaji_pokok + tunj_tetap + tunj_lain + overtime
        bruto_reguler_tahunan = bruto_reguler_bulanan * 12

        # Total bruto (termasuk THR/bonus untuk pelaporan)
        penghasilan_bruto = bruto_reguler_bulanan + bonus_thr
        penghasilan_bruto_tahunan = bruto_reguler_tahunan + bonus_thr

        # ── 2. Biaya Jabatan (5%, maks 6 juta/tahun) ───────────────────────
        biaya_jabatan = min(bruto_reguler_tahunan * BIAYA_JABATAN_RATE, BIAYA_JABATAN_MAX)

        # ── 3. Iuran BPJS (pengurang — hanya dari gaji reguler) ────────────
        jht_emp = lines_dict.get('IDN_BPJS_TK_JHT_EMP', 0.0) * 12
        jp_emp  = lines_dict.get('IDN_BPJS_TK_JP_EMP', 0.0) * 12

        total_pengurang = biaya_jabatan + jht_emp + jp_emp

        # ── 4. PTKP & PKP gaji reguler ─────────────────────────────────────
        ptkp_status = emp.ptkp_status or 'TK/0'
        ptkp_amount = PTKP_TABLE.get(ptkp_status, 54_000_000)
        penghasilan_neto_reguler = bruto_reguler_tahunan - total_pengurang
        pkp_gaji_tahunan = max(penghasilan_neto_reguler - ptkp_amount, 0)
        pkp_gaji_tahunan = (pkp_gaji_tahunan // 1000) * 1000

        # ── 5. PPh 21 gaji reguler (progresif) ─────────────────────────────
        pph21_reguler_tahunan = hitung_pph21_progresif(pkp_gaji_tahunan)

        # ── 6. PPh 21 atas bonus/THR (terpisah) ────────────────────────────
        pph21_bonus = self._hitung_pph21_bonus_thr(
            bonus_thr, emp, ptkp_amount, pkp_gaji_tahunan
        )

        # ── 7. Surcharge jika tidak ada NPWP ────────────────────────────────
        surcharge_reguler = 0.0
        surcharge_bonus = 0.0
        if not emp.npwp_has:
            surcharge_reguler = pph21_reguler_tahunan * TANPA_NPWP_SURCHARGE
            pph21_reguler_tahunan += surcharge_reguler
            surcharge_bonus = pph21_bonus * TANPA_NPWP_SURCHARGE
            pph21_bonus += surcharge_bonus

        # ── 8. PPh 21 reguler bulanan ──────────────────────────────────────
        pph21_reguler_bulanan = pph21_reguler_tahunan / 12

        # ── 9. Penghasilan neto & PKP total (untuk pelaporan) ──────────────
        penghasilan_neto = penghasilan_bruto_tahunan - total_pengurang
        pkp_tahunan = max(penghasilan_neto - ptkp_amount, 0)
        pkp_tahunan = (pkp_tahunan // 1000) * 1000
        pph21_tahunan_total = hitung_pph21_progresif(pkp_tahunan)

        # ── 10. Penyesuaian bulan Desember ──────────────────────────────────
        is_december = date_from.month == 12
        akumulasi_jan_nov = 0.0

        if is_december:
            akumulasi_jan_nov = self._get_akumulasi_pph21(emp.id, date_from.year)
            pph21_final = pph21_reguler_tahunan - akumulasi_jan_nov + pph21_bonus
        else:
            pph21_final = pph21_reguler_bulanan + pph21_bonus

        # ── 11. Simpan rincian ─────────────────────────────────────────────
        existing = self.search([('payslip_id', '=', payslip.id)], limit=1)
        vals = {
            'payslip_id':                          payslip.id,
            'gaji_pokok':                          gaji_pokok,
            'tunjangan_tetap':                     tunj_tetap,
            'tunjangan_lain':                      tunj_lain,
            'overtime':                            overtime,
            'bonus_thr':                           bonus_thr,
            'penghasilan_bruto_reguler':           bruto_reguler_bulanan,
            'penghasilan_bruto_reguler_tahunan':   bruto_reguler_tahunan,
            'penghasilan_bruto':                   penghasilan_bruto,
            'penghasilan_bruto_tahunan':           penghasilan_bruto_tahunan,
            'biaya_jabatan':                       biaya_jabatan / 12,
            'bpjs_tk_jht_emp':                     jht_emp / 12,
            'bpjs_tk_jp_emp':                      jp_emp / 12,
            'total_pengurang':                     total_pengurang / 12,
            'ptkp_status':                         ptkp_status,
            'ptkp_amount':                         ptkp_amount,
            'penghasilan_neto':                    penghasilan_neto,
            'pkp_tahunan':                         pkp_tahunan,
            'pph21_tahunan':                       pph21_reguler_tahunan,
            'pph21_bulanan':                       pph21_reguler_bulanan,
            'pph21_bonus_thr':                     pph21_bonus,
            'pph21_surcharge':                     (surcharge_reguler + surcharge_bonus) / 12,
            'pph21_final':                         pph21_final,
            'pph21_akumulasi_jan_nov':             akumulasi_jan_nov,
            'is_december_adj':                     is_december,
            'npwp_has':                            emp.npwp_has,
            'note': f'Dihitung otomatis — {date_from.strftime("%B %Y")}',
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)

        return pph21_final
