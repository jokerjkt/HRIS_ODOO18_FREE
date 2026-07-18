# -*- coding: utf-8 -*-
"""
THR (Tunjangan Hari Raya) Calculator
======================================
Menghitung THR sesuai PP No. 36 Tahun 2021.

Aturan:
- Masa kerja >= 12 bulan: THR = 1x gaji/upah sebulan
- Masa kerja 1-12 bulan: THR = (masa_kerja / 12) x gaji sebulan
- Masa kerja < 1 bulan : tidak berhak THR
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrThr(models.Model):
    _name = 'hr.thr'
    _description = 'Tunjangan Hari Raya (THR)'
    _inherit = ['mail.thread', 'trial.mixin']
    _order = 'year desc, employee_id'

    name = fields.Char(string='Nomor THR', readonly=True, default='/')
    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        store=True,
    )
    year = fields.Integer(
        string='Tahun',
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    religious_holiday = fields.Selection(
        selection=[
            ('lebaran', 'Idul Fitri (Lebaran)'),
            ('natal',   'Natal'),
            ('nyepi',   'Nyepi'),
            ('waisak',  'Waisak'),
            ('imlek',   'Imlek'),
        ],
        string='Hari Raya',
        required=True,
        default='lebaran',
    )

    # ── Masa Kerja ────────────────────────────────────────────────────────────
    join_date = fields.Date(
        related='employee_id.join_date',
        string='Tanggal Bergabung',
        store=True,
    )
    thr_date = fields.Date(
        string='Tanggal Pembayaran THR',
        required=True,
        default=lambda self: fields.Date.today(),
        help='Minimal 7 hari sebelum hari raya (PP 36/2021)',
    )
    tenure_months = fields.Integer(
        string='Masa Kerja (Bulan)',
        compute='_compute_thr_amount',
        store=True,
    )

    # ── Kalkulasi ─────────────────────────────────────────────────────────────
    monthly_wage = fields.Float(
        string='Gaji Sebulan (Rp)',
        compute='_compute_thr_amount',
        store=True,
        help='Gaji pokok + tunjangan tetap dari kontrak aktif',
    )
    thr_proportion = fields.Float(
        string='Proporsi THR',
        compute='_compute_thr_amount',
        store=True,
        help='1.0 jika >= 12 bulan, proporsional jika < 12 bulan',
    )
    thr_amount = fields.Float(
        string='Jumlah THR (Rp)',
        compute='_compute_thr_amount',
        store=True,
    )
    thr_amount_manual = fields.Float(
        string='Jumlah THR (Override Manual)',
        help='Isi jika ingin mengganti nilai THR dari hasil perhitungan otomatis',
    )
    thr_final = fields.Float(
        string='THR Final (Rp)',
        compute='_compute_thr_final',
        store=True,
    )

    # ── Status ────────────────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Dikonfirmasi'),
            ('paid', 'Sudah Dibayar'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
    )
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Slip Gaji THR',
        readonly=True,
        copy=False,
    )
    note = fields.Text('Keterangan')

    # ────────────────────────────────────────────────────────────────────────
    # Compute Methods
    # ────────────────────────────────────────────────────────────────────────

    @api.depends('employee_id', 'thr_date')
    def _compute_thr_amount(self):
        for rec in self:
            if not rec.employee_id or not rec.thr_date:
                rec.tenure_months = 0
                rec.monthly_wage = 0.0
                rec.thr_proportion = 0.0
                rec.thr_amount = 0.0
                continue

            # Masa kerja
            join = rec.employee_id.join_date or rec.thr_date
            months = (
                (rec.thr_date.year - join.year) * 12
                + (rec.thr_date.month - join.month)
            )
            rec.tenure_months = max(months, 0)

            # Gaji dari kontrak aktif
            contract = rec.employee_id.contract_id
            wage = contract.wage if contract else 0.0
            rec.monthly_wage = wage

            # Proporsi THR
            if rec.tenure_months >= 12:
                rec.thr_proportion = 1.0
            elif rec.tenure_months >= 1:
                rec.thr_proportion = rec.tenure_months / 12.0
            else:
                rec.thr_proportion = 0.0

            rec.thr_amount = wage * rec.thr_proportion

    @api.depends('thr_amount', 'thr_amount_manual')
    def _compute_thr_final(self):
        for rec in self:
            rec.thr_final = rec.thr_amount_manual if rec.thr_amount_manual > 0 else rec.thr_amount

    # ────────────────────────────────────────────────────────────────────────
    # CRUD
    # ────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        self._enforce_trial()
        return super().create(vals_list)

    # ────────────────────────────────────────────────────────────────────────
    # Actions
    # ────────────────────────────────────────────────────────────────────────

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Hanya THR dengan status Draft yang bisa dikonfirmasi.')
            if rec.thr_final <= 0:
                raise UserError('Jumlah THR tidak valid. Periksa masa kerja dan gaji karyawan.')
            if rec.name == '/':
                rec.name = self.env['ir.sequence'].next_by_code('hr.thr') or '/'
            rec.state = 'confirmed'

    def action_mark_paid(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError('Konfirmasi THR terlebih dahulu sebelum menandai sudah dibayar.')
            rec.state = 'paid'

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError('THR yang sudah dibayar tidak dapat direset.')
            rec.state = 'draft'
