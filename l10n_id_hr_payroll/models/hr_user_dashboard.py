# -*- coding: utf-8 -*-
"""
HR User Dashboard — Simplified dashboard for HR users
======================================================
For regular HR users (hr.group_hr_user).
Shows attendance, leave, payslip, quick actions.
"""
from datetime import datetime, time
from odoo import models, fields, api


class HrUserDashboard(models.TransientModel):
    _name = 'hr.user.dashboard'
    _description = 'Dashboard HR User'

    # ── Attendance ───────────────────────────────────────────────────────────
    hadir_hari_ini = fields.Integer(
        string='Hadir Hari Ini',
        compute='_compute_stats',
    )
    tidak_hadir_hari_ini = fields.Integer(
        string='Tidak Hadir Hari Ini',
        compute='_compute_stats',
    )

    # ── Leave ────────────────────────────────────────────────────────────────
    cuti_pending = fields.Integer(
        string='Cuti Pending',
        compute='_compute_stats',
    )
    cuti_sakit = fields.Integer(
        string='Cuti Sakit (Bulan Ini)',
        compute='_compute_stats',
    )

    # ── Payslip ──────────────────────────────────────────────────────────────
    payslip_draft_count = fields.Integer(
        string='Slip Gaji Draft',
        compute='_compute_stats',
    )
    payslip_computed_count = fields.Integer(
        string='Slip Gaji Siap',
        compute='_compute_stats',
    )

    # ── Expense ──────────────────────────────────────────────────────────────
    expense_pending = fields.Integer(
        string='Expense Pending',
        compute='_compute_stats',
    )

    # ── Employee ─────────────────────────────────────────────────────────────
    employee_count = fields.Integer(
        string='Karyawan Aktif',
        compute='_compute_stats',
    )

    # ── Overtime ─────────────────────────────────────────────────────────────
    overtime_pending_count = fields.Integer(
        string='Lembur Pending',
        compute='_compute_stats',
    )

    # ── Trial Info ───────────────────────────────────────────────────────────
    trial_days_left = fields.Integer(
        compute='_compute_trial_info',
    )
    trial_expired = fields.Boolean(
        compute='_compute_trial_info',
    )
    trial_message = fields.Text(
        compute='_compute_trial_info',
    )

    @api.depends()
    def _compute_stats(self):
        today = fields.Date.today()
        for rec in self:
            rec.employee_count = self.env['hr.employee'].search_count(
                [('active', '=', True)]
            )

            # Attendance
            day_start = datetime.combine(today, time.min)
            day_end = datetime.combine(today, time.max)
            rec.hadir_hari_ini = self.env['hr.attendance'].search_count([
                ('check_in', '>=', day_start),
                ('check_in', '<=', day_end),
            ])
            rec.tidak_hadir_hari_ini = max(
                rec.employee_count - rec.hadir_hari_ini, 0
            )

            # Payslip
            rec.payslip_draft_count = self.env['hr.payslip'].search_count(
                [('state', '=', 'draft')]
            )
            rec.payslip_computed_count = self.env['hr.payslip'].search_count(
                [('state', '=', 'computed')]
            )

            # Overtime
            rec.overtime_pending_count = self.env['hr.overtime'].search_count(
                [('state', '=', 'submitted')]
            )

            # Leave
            rec.cuti_pending = self.env['hr.leave'].search_count(
                [('state', '=', 'confirm')]
            )
            month_start = today.replace(day=1)
            sick_type = self.env['hr.leave.type'].search(
                [('name', 'ilike', 'Cuti Sakit')], limit=1
            )
            rec.cuti_sakit = self.env['hr.leave'].search_count([
                ('request_date_from', '>=', month_start),
                ('request_date_to', '<=', today),
                ('holiday_status_id', '=', sick_type.id),
            ]) if sick_type else 0

            # Expense
            has_expense = self.env['ir.module.module'].search_count([
                ('name', '=', 'hr_expense'), ('state', '=', 'installed')
            ])
            if has_expense:
                rec.expense_pending = self.env['hr.expense'].search_count(
                    [('state', 'in', ['draft', 'reported', 'submitted'])]
                )
            else:
                rec.expense_pending = 0

    @api.depends()
    def _compute_trial_info(self):
        for rec in self:
            info = self.env['hr.payslip']._get_trial_info()
            rec.trial_days_left = info['days_left']
            rec.trial_expired = info['expired']
            rec.trial_message = info['message']

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_open_my_payslips(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Slip Gaji',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
        }

    def action_open_overtime_pending(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lembur Perlu Persetujuan',
            'res_model': 'hr.overtime',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'submitted')],
        }

    def action_open_thr(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'THR',
            'res_model': 'hr.thr',
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
            'domain': [('state', '=', 'draft')],
        }
