# -*- coding: utf-8 -*-
"""
Employee Loan Model
===================
Pinjaman karyawan dengan cicilan otomatis dari slip gaji.
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrLoan(models.Model):
    _name = 'hr.loan'
    _description = 'Pinjaman Karyawan'
    _inherit = ['mail.thread', 'trial.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='No. Pinjaman', readonly=True, copy=False, default='/')
    employee_id = fields.Many2one('hr.employee', string='Karyawan', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', string='Perusahaan',
                                  default=lambda self: self.env.company, required=True)
    loan_type = fields.Selection([
        ('installment', 'Cicilan (Potong Gaji)'),
        ('full', 'Bayar Langsung (Lunas)'),
    ], string='Tipe Pinjaman', required=True, default='installment', tracking=True)
    loan_amount = fields.Float(string='Jumlah Pinjaman', required=True, tracking=True)
    installment_amount = fields.Float(string='Cicilan/Bulan', tracking=True)
    installment_months = fields.Integer(string='Jumlah Bulan', tracking=True)
    total_paid = fields.Float(string='Sudah Terbayar', compute='_compute_total_paid', store=True)
    remaining = fields.Float(string='Sisa Hutang', compute='_compute_remaining', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Disetujui'),
        ('running', 'Berjalan'),
        ('done', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='draft', tracking=True)
    loan_date = fields.Date(string='Tanggal Pinjaman', default=fields.Date.today, required=True)
    approved_date = fields.Date(string='Tanggal Persetujuan')
    note = fields.Text(string='Keterangan')
    loan_line_ids = fields.One2many('hr.loan.line', 'loan_id', string='Detail Cicilan')
    payslip_ids = fields.One2many('hr.payslip', 'loan_id', string='Slip Gaji Terkait')

    @api.depends('loan_line_ids.paid', 'loan_line_ids.amount')
    def _compute_total_paid(self):
        for rec in self:
            paid_lines = rec.loan_line_ids.filtered(lambda l: l.paid)
            rec.total_paid = sum(paid_lines.mapped('amount'))

    @api.depends('loan_amount', 'total_paid')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining = max(rec.loan_amount - rec.total_paid, 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        self._enforce_trial()
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan') or 'LOAN-001'
        return super().create(vals_list)

    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Hanya pinjaman draft yang bisa disetujui.')
            rec.state = 'approved'
            rec.approved_date = fields.Date.today()

    def action_start(self):
        """Mulai cicilan — generate loan lines."""
        for rec in self:
            if rec.state != 'approved':
                raise UserError('Pinjaman harus disetujui terlebih dahulu.')
            if rec.loan_type == 'installment':
                if not rec.installment_amount or rec.installment_amount <= 0:
                    raise UserError('Cicilan per bulan harus diisi dan lebih dari 0.')
                if not rec.installment_months or rec.installment_months <= 0:
                    raise UserError('Jumlah bulan harus diisi dan lebih dari 0.')
                rec._generate_loan_lines()
            rec.state = 'running'

    def _generate_loan_lines(self):
        """Generate detail cicilan per bulan."""
        self.loan_line_ids.unlink()
        today = fields.Date.today()
        for i in range(self.installment_months):
            due_date = fields.Date.add(today, months=i + 1)
            self.env['hr.loan.line'].create({
                'loan_id': self.id,
                'sequence': i + 1,
                'due_date': due_date,
                'amount': self.installment_amount,
                'paid': False,
            })

    def action_done(self):
        for rec in self:
            if rec.remaining > 0:
                raise UserError('Masih ada sisa hutang yang belum dibayar.')
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            if rec.state in ('done',):
                raise UserError('Pinjaman yang sudah selesai tidak bisa dibatalkan.')
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError('Hanya pinjaman dibatalkan yang bisa di-reset.')
            rec.state = 'draft'

    def get_installment_for_payslip(self, date_from, date_to):
        """Return installment line for payslip period."""
        self.ensure_one()
        if self.loan_type != 'installment' or self.state != 'running':
            return False
        if self.remaining <= 0:
            return False
        # Find unpaid line within period
        line = self.loan_line_ids.filtered(
            lambda l: not l.paid and l.due_date >= date_from and l.due_date <= date_to
        )
        return line[:1] if line else False


class HrLoanLine(models.Model):
    _name = 'hr.loan.line'
    _description = 'Detail Cicilan Pinjaman'

    loan_id = fields.Many2one('hr.loan', string='Pinjaman', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='loan_id.employee_id', store=True)
    sequence = fields.Integer(string='Urutan')
    due_date = fields.Date(string='Tanggal Jatuh Tempo')
    amount = fields.Float(string='Jumlah Cicilan')
    paid = fields.Boolean(string='Sudah Dibayar', default=False)
    paid_date = fields.Date(string='Tanggal Pembayaran')
    payslip_id = fields.Many2one('hr.payslip', string='Slip Gaji', readonly=True)
