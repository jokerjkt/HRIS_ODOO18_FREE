# -*- coding: utf-8 -*-
"""
Payroll Dashboard TransientModel (Admin)
=========================================
Dashboard untuk Admin HR — ringkasan payroll, attendance, leave, skills, expense.
"""
from datetime import datetime, time, date
from odoo import models, fields, api


class HrPayrollDashboard(models.TransientModel):
    _name = 'hr.payroll.dashboard'
    _description = 'Dashboard Payroll Indonesia'

    # ── Attendance Fields ────────────────────────────────────────────────────
    hadir_hari_ini = fields.Integer(
        string='Hadir Hari Ini',
        compute='_compute_attendance',
    )
    tidak_hadir_hari_ini = fields.Integer(
        string='Tidak Hadir Hari Ini',
        compute='_compute_attendance',
    )
    jam_lembur_bulan_ini = fields.Float(
        string='Jam Lembur Bulan Ini',
        compute='_compute_attendance',
    )

    # ── Leave Fields ─────────────────────────────────────────────────────────
    cuti_disetujui = fields.Integer(
        string='Cuti Disetujui (Bulan Ini)',
        compute='_compute_leave',
    )
    cuti_pending = fields.Integer(
        string='Cuti Pending',
        compute='_compute_leave',
    )
    cuti_sakit = fields.Integer(
        string='Cuti Sakit (Bulan Ini)',
        compute='_compute_leave',
    )
    cuti_tanpa_gaji = fields.Integer(
        string='Cuti Tanpa Gaji (Bulan Ini)',
        compute='_compute_leave',
    )

    # ── Skills Fields ────────────────────────────────────────────────────────
    total_skill_types = fields.Integer(
        string='Jenis Skill',
        compute='_compute_skills',
    )
    karyawan_with_skill = fields.Integer(
        string='Karyawan dengan Skill',
        compute='_compute_skills',
    )

    # ── Expense Fields ───────────────────────────────────────────────────────
    expense_pending = fields.Integer(
        string='Expense Pending',
        compute='_compute_expense',
    )
    expense_approved = fields.Integer(
        string='Expense Approved',
        compute='_compute_expense',
    )
    expense_total_amount = fields.Float(
        string='Total Expense (Rp)',
        compute='_compute_expense',
    )

    # ── Existing Payroll Fields ──────────────────────────────────────────────
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
    total_penghasilan = fields.Float(
        string='Total Penghasilan Bulan Ini (Rp)',
        compute='_compute_summary',
    )

    # ── Trial Info ───────────────────────────────────────────────────────────
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

    # ────────────────────────────────────────────────────────────────────────
    # Compute Methods
    # ────────────────────────────────────────────────────────────────────────

    @api.depends()
    def _compute_trial_info(self):
        for rec in self:
            info = self.env['hr.payslip']._get_trial_info()
            rec.trial_days_left = info['days_left']
            rec.trial_expired = info['expired']
            rec.trial_message = info['message']

    @api.depends()
    def _compute_attendance(self):
        today = fields.Date.today()
        for rec in self:
            day_start = datetime.combine(today, time.min)
            day_end = datetime.combine(today, time.max)
            rec.hadir_hari_ini = self.env['hr.attendance'].search_count([
                ('check_in', '>=', day_start),
                ('check_in', '<=', day_end),
            ])
            total_active = self.env['hr.employee'].search_count([('active', '=', True)])
            rec.tidak_hadir_hari_ini = max(total_active - rec.hadir_hari_ini, 0)
            month_start = today.replace(day=1)
            attendances = self.env['hr.attendance'].search([
                ('check_in', '>=', month_start),
                ('check_in', '<=', today),
            ])
            rec.jam_lembur_bulan_ini = sum(attendances.mapped('overtime_hours'))

    @api.depends()
    def _compute_leave(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        domain_month = [
            ('request_date_from', '>=', month_start),
            ('request_date_to', '<=', today),
        ]
        for rec in self:
            rec.cuti_disetujui = self.env['hr.leave'].search_count(
                domain_month + [('state', '=', 'validate')]
            )
            rec.cuti_pending = self.env['hr.leave'].search_count(
                [('state', '=', 'confirm')]
            )
            sick_type = self.env['hr.leave.type'].search(
                [('name', 'ilike', 'Cuti Sakit')], limit=1
            )
            rec.cuti_sakit = self.env['hr.leave'].search_count(
                domain_month + [('holiday_status_id', '=', sick_type.id)]
            ) if sick_type else 0
            unpaid_type = self.env['hr.leave.type'].search(
                [('name', 'ilike', 'Cuti Tanpa Gaji')], limit=1
            )
            rec.cuti_tanpa_gaji = self.env['hr.leave'].search_count(
                domain_month + [('holiday_status_id', '=', unpaid_type.id)]
            ) if unpaid_type else 0

    @api.depends()
    def _compute_skills(self):
        for rec in self:
            rec.total_skill_types = self.env['hr.skill.type'].search_count([])
            skill_employees = self.env['hr.employee.skill'].search([])
            rec.karyawan_with_skill = len(set(skill_employees.mapped('employee_id').ids))

    @api.depends()
    def _compute_expense(self):
        has_expense = self.env['ir.module.module'].search_count([
            ('name', '=', 'hr_expense'), ('state', '=', 'installed')
        ])
        for rec in self:
            if has_expense:
                rec.expense_pending = self.env['hr.expense'].search_count(
                    [('state', 'in', ['draft', 'reported', 'submitted'])]
                )
                rec.expense_approved = self.env['hr.expense'].search_count(
                    [('state', '=', 'approved')]
                )
                done_expenses = self.env['hr.expense'].search([('state', '=', 'done')])
                rec.expense_total_amount = sum(done_expenses.mapped('total_amount'))
            else:
                rec.expense_pending = 0
                rec.expense_approved = 0
                rec.expense_total_amount = 0.0

    @api.depends()
    def _compute_summary(self):
        for rec in self:
            rec.employee_count = self.env['hr.employee'].search_count([('active', '=', True)])

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

            today = fields.Date.today()
            month_start = today.replace(day=1)
            done_slips = self.env['hr.payslip'].search([
                ('state', '=', 'done'),
                ('date_from', '>=', month_start),
                ('date_from', '<=', today),
            ])
            rec.total_penghasilan = sum(done_slips.mapped('net_wage'))

    # ── Action Methods ───────────────────────────────────────────────────────

    def action_open_employees(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Karyawan',
            'res_model': 'hr.employee',
            'view_mode': 'list,form',
            'domain': [('active', '=', True)],
        }

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

    def action_open_bpjs_settings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarif BPJS',
            'res_model': 'hr.bpjs.rate',
            'view_mode': 'list,form',
        }

    def action_open_leave_all(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cuti',
            'res_model': 'hr.leave',
            'view_mode': 'list,form',
        }

    def action_open_leave_pending(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cuti — Pending',
            'res_model': 'hr.leave',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'confirm')],
        }

    def action_open_attendance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Absensi Hari Ini',
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
        }

    def action_open_expense_pending(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expense — Pending',
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('state', 'in', ['draft', 'reported', 'submitted'])],
        }

    def action_open_expense_approved(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expense — Approved',
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'approved')],
        }

    def action_open_skills(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Skill Karyawan',
            'res_model': 'hr.employee.skill',
            'view_mode': 'list,form',
        }
