# -*- coding: utf-8 -*-
"""
HR User Dashboard — Simplified dashboard for HR users
======================================================
For regular HR users (hr.group_hr_user).
Shows pending approvals, team stats, quick actions.
"""
from odoo import models, fields, api


class HrUserDashboard(models.TransientModel):
    _name = 'hr.user.dashboard'
    _description = 'Dashboard HR User'

    # Employee Stats
    employee_count = fields.Integer(
        compute='_compute_stats',
    )

    # Payslip Stats
    payslip_draft_count = fields.Integer(
        compute='_compute_stats',
    )
    payslip_computed_count = fields.Integer(
        compute='_compute_stats',
    )

    # Overtime Stats
    overtime_pending_count = fields.Integer(
        compute='_compute_stats',
    )

    # THR Stats
    thr_pending_count = fields.Integer(
        compute='_compute_stats',
    )

    # Trial Info
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
        for rec in self:
            rec.employee_count = self.env['hr.employee'].search_count(
                [('active', '=', True)]
            )
            rec.payslip_draft_count = self.env['hr.payslip'].search_count(
                [('state', '=', 'draft')]
            )
            rec.payslip_computed_count = self.env['hr.payslip'].search_count(
                [('state', '=', 'computed')]
            )
            rec.overtime_pending_count = self.env['hr.overtime'].search_count(
                [('state', '=', 'submitted')]
            )
            rec.thr_pending_count = self.env['hr.thr'].search_count(
                [('state', '=', 'draft')]
            )

    @api.depends()
    def _compute_trial_info(self):
        for rec in self:
            info = self.env['hr.payslip']._get_trial_info()
            rec.trial_days_left = info['days_left']
            rec.trial_expired = info['expired']
            rec.trial_message = info['message']

    # Actions
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
