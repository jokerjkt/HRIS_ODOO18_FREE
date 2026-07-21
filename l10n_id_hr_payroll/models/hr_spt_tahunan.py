# -*- coding: utf-8 -*-
"""
SPT Tahunan — Annual Tax Return Aggregator
==========================================
Aggregates 12 months of PPh 21 data per employee per year.
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrSptTahunan(models.Model):
    _name = 'hr.spt.tahunan'
    _description = 'SPT Tahunan PPh 21'
    _inherit = ['trial.mixin']
    _order = 'year desc, employee_id'
    _rec_name = 'display_name'

    name = fields.Char(string='No. SPT', readonly=True, copy=False)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Karyawan', required=True)
    year = fields.Integer(string='Tahun Pajak', required=True,
                          default=lambda self: fields.Date.today().year)
    pph21_ids = fields.One2many('hr.pph21', 'employee_id', string='Detail PPh 21')

    # Aggregated income
    total_gaji_pokok = fields.Float(string='Total Gaji Pokok')
    total_tunj_tetap = fields.Float(string='Total Tunjangan Tetap')
    total_tunj_lain = fields.Float(string='Total Tunjangan Tidak Tetap')
    total_bonus_thr = fields.Float(string='Total Bonus/THR')
    total_bruto = fields.Float(string='Total Penghasilan Bruto')
    total_pengurang = fields.Float(string='Total Pengurang')
    total_bruto_12_bulan = fields.Float(string='Bruto 12 Bulan (Tanpa THR)')

    # BPJS
    total_bpjs_tk = fields.Float(string='Total BPJS TK (Karyawan)')
    total_bpjs_kes = fields.Float(string='Total BPJS Kes (Karyawan)')

    # Tax
    ptkp_status = fields.Char(string='Status PTKP')
    ptkp_amount = fields.Float(string='PTKP (Rp)')
    pkp_annual = fields.Float(string='PKP Setahun')
    pph21_terutang = fields.Float(string='PPh 21 Terutang Setahun')
    pph21_sudah_dipotong = fields.Float(string='PPh 21 Sudah Dipotong (12 bln)')
    pph21_bonus_thr = fields.Float(string='PPh 21 Bonus/THR')
    sisa_kurang_bayar = fields.Float(string='Sisa Kurang Bayar / (Lebih Bayar)')
    pph21_bulan_desember = fields.Float(string='PPh 21 Bulan Desember')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi'),
        ('submitted', 'Terkirim'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('employee_id', 'year')
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or ''
            rec.display_name = f'SPT {rec.year} — {emp}'

    @api.model
    def create(self, vals_list):
        self._enforce_trial()
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.spt.tahunan.sequence'
                ) or '/'
        return super().create(vals_list)

    def action_compute(self):
        """Aggregate PPh 21 data dari semua slip gaji tahun ini."""
        for rec in self:
            pph21_records = self.env['hr.pph21'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('period_year', '=', rec.year),
            ], order='period_month')

            if not pph21_records:
                raise UserError(
                    f'Tidak ada data PPh 21 untuk {rec.employee_id.name} tahun {rec.year}.\n'
                    'Hitung gaji terlebih dahulu.'
                )

            # Aggregate income (12 months, exclude THR/bonus yang sudah terpisah)
            rec.total_gaji_pokok = sum(pph21_records.mapped('gaji_pokok')) * 12
            rec.total_tunj_tetap = sum(pph21_records.mapped('tunjangan_tetap')) * 12
            rec.total_tunj_lain = sum(pph21_records.mapped('tunjangan_lain')) * 12
            rec.total_bonus_thr = sum(pph21_records.mapped('bonus_thr'))
            rec.total_bruto_12_bulan = rec.total_gaji_pokok + rec.total_tunj_tetap + rec.total_tunj_lain
            rec.total_bruto = rec.total_bruto_12_bulan + rec.total_bonus_thr

            # BPJS
            rec.total_bpjs_tk = sum(pph21_records.mapped('bpjs_tk_jht_emp')) * 12
            rec.total_bpjs_kes = 0.0  # BPJS Kes is separate from PPh 21 deduction

            # Pengurang
            biaya_jabatan = sum(pph21_records.mapped('biaya_jabatan')) * 12
            iuran_pensiun = sum(pph21_records.mapped('iuran_pensiun_emp')) * 12
            rec.total_pengurang = biaya_jabatan + iuran_pensiun + rec.total_bpjs_tk

            # PTKP & PKP
            pph_first = pph21_records[0]
            rec.ptkp_status = pph_first.ptkp_status
            rec.ptkp_amount = pph_first.ptkp_amount
            rec.pkp_annual = pph_first.pkp_tahunan

            # PPh 21 terutang
            rec.pph21_terutang = pph_first.pph21_tahunan

            # PPh 21 sudah dipotong (Jan-Nov reguler + Desember + bonus/THR)
            rec.pph21_sudah_dipotong = sum(pph21_records.mapped('pph21_final'))

            # PPh 21 bonus/THR
            rec.pph21_bonus_thr = sum(pph21_records.mapped('pph21_bonus_thr'))

            # PPh 21 Desember
            des_record = pph21_records.filtered(lambda r: r.period_month == 12)
            rec.pph21_bulan_desember = des_record.pph21_final if des_record else 0.0

            # Sisa
            rec.sisa_kurang_bayar = rec.pph21_terutang - rec.pph21_sudah_dipotong

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Hanya SPT draft yang bisa dikonfirmasi.')
            if rec.pph21_terutang <= 0:
                raise UserError('Hitung SPT terlebih dahulu.')
            rec.state = 'confirmed'

    def action_export_ebupot(self):
        """Export ke e-Bupot."""
        self.ensure_one()
        ebupot = self.env['hr.ebupot'].create({
            'employee_id': self.employee_id.id,
            'year': self.year,
            'form_type': '1721A1',
        })
        ebupot.action_compute_from_payslip()
        ebupot.action_generate_xml()
        return {
            'type': 'ir.actions.act_window',
            'name': 'e-Bupot',
            'res_model': 'hr.ebupot',
            'res_id': ebupot.id,
            'view_mode': 'form',
            'target': 'new',
        }
