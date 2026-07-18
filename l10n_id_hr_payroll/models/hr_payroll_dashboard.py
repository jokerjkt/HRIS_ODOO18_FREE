# -*- coding: utf-8 -*-
"""
Payroll Dashboard TransientModel
=================================
Model dashboard untuk menampilkan ringkasan payroll Indonesia.
Digunakan sebagai backend dashboard agar tidak membuka form create employee.
"""
from odoo import models, fields, api


class HrPayrollDashboard(models.TransientModel):
    _name = 'hr.payroll.dashboard'
    _description = 'Dashboard Payroll Indonesia'

    # ── Summary Fields ────────────────────────────────────────────────────────
    payslip_count = fields.Integer(
        string='Total Slip Gaji',
        compute='_compute_summary',
    )
    payslip_draft_count = fields.Integer(
        string='Slip Gaji Draft',
        compute='_compute_summary',
    )
    overtime_pending_count = fields.Integer(
        string='Lembur Perlu Disetujui',
        compute='_compute_summary',
    )
    overtime_approved_count = fields.Integer(
        string='Lembur Disetujui (Belum di Payslip)',
        compute='_compute_summary',
    )
    thr_count = fields.Integer(
        string='Total THR',
        compute='_compute_summary',
    )
    thr_pending_count = fields.Integer(
        string='THR Draft',
        compute='_compute_summary',
    )
    employee_count = fields.Integer(
        string='Karyawan Aktif',
        compute='_compute_summary',
    )
    bpjs_rate_count = fields.Integer(
        string='Kelompok Risiko BPJS',
        compute='_compute_summary',
    )

    # ── Trial Info ──────────────────────────────────────────────────────────
    trial_days_left = fields.Integer(
        string='Sisa Hari Uji Coba',
        compute='_compute_trial_info',
    )
    trial_expired = fields.Boolean(
        string='Uji Coba Berakhir',
        compute='_compute_trial_info',
    )
    trial_message = fields.Text(
        string='Pesan Uji Coba',
        compute='_compute_trial_info',
    )

    @api.depends()
    def _compute_trial_info(self):
        for rec in self:
            info = self.env['hr.payslip']._get_trial_info()
            rec.trial_days_left = info['days_left']
            rec.trial_expired = info['expired']
            rec.trial_message = info['message']

    @api.depends()
    def _compute_summary(self):
        for rec in self:
            emp_model = self.env['hr.employee']
            rec.employee_count = emp_model.search_count([('active', '=', True)])

            payslip_model = self.env['hr.payslip']
            rec.payslip_count = payslip_model.search_count([])
            rec.payslip_draft_count = payslip_model.search_count([('state', '=', 'draft')])

            ot_model = self.env['hr.overtime']
            rec.overtime_pending_count = ot_model.search_count([('state', '=', 'submitted')])
            rec.overtime_approved_count = ot_model.search_count([
                ('state', '=', 'approved'),
                ('payslip_id', '=', False),
            ])

            thr_model = self.env['hr.thr']
            rec.thr_count = thr_model.search_count([])
            rec.thr_pending_count = thr_model.search_count([('state', '=', 'draft')])

            rec.bpjs_rate_count = self.env['hr.bpjs.rate'].search_count([])

    # ── Action Methods ────────────────────────────────────────────────────────
    def action_open_payslips(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Slip Gaji',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
        }

    def action_open_payslip_draft(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Slip Gaji — Draft',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'draft')],
        }

    def action_open_overtime_pending(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lembur — Perlu Persetujuan',
            'res_model': 'hr.overtime',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'submitted')],
        }

    def action_open_overtime_approved(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lembur — Belum di Payslip',
            'res_model': 'hr.overtime',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'approved'), ('payslip_id', '=', False)],
        }

    def action_open_thr(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'THR',
            'res_model': 'hr.thr',
            'view_mode': 'list,form',
        }

    def action_open_thr_pending(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'THR — Draft',
            'res_model': 'hr.thr',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'draft')],
        }

    def action_open_employees(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Karyawan',
            'res_model': 'hr.employee',
            'view_mode': 'list,form',
            'domain': [('active', '=', True)],
        }

    def action_open_bpjs_settings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarif BPJS',
            'res_model': 'hr.bpjs.rate',
            'view_mode': 'list,form',
        }
