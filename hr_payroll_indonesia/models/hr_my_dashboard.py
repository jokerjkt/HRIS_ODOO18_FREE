# -*- coding: utf-8 -*-
"""
My Dashboard — Personal dashboard for logged-in employee
========================================================
Shows the employee's own payslips, overtime, leaves, expenses, attendance, shift.
"""
from datetime import datetime, time
from odoo import models, fields, api


class HrMyDashboard(models.TransientModel):
    _name = 'hr.my.dashboard'
    _description = 'Dashboard Personal Karyawan'

    # ── Employee Info ────────────────────────────────────────────────────────
    employee_name = fields.Char(string='Nama', compute='_compute_my_data')
    employee_department = fields.Char(string='Departemen', compute='_compute_my_data')
    employee_job = fields.Char(string='Jabatan', compute='_compute_my_data')
    employee_nik = fields.Char(string='NIK', compute='_compute_my_data')
    employee_npwp = fields.Char(string='NPWP', compute='_compute_my_data')
    employee_ptkp = fields.Char(string='PTKP', compute='_compute_my_data')
    employee_bank_name = fields.Char(string='Bank', compute='_compute_my_data')
    employee_bank_account = fields.Char(string='No. Rekening', compute='_compute_my_data')
    employee_join_date = fields.Date(string='Tanggal Bergabung', compute='_compute_my_data')

    # ── My Payslips ──────────────────────────────────────────────────────────
    my_payslip_count = fields.Integer(string='Total Slip Gaji', compute='_compute_my_data')
    my_payslip_draft = fields.Integer(string='Slip Gaji Draft', compute='_compute_my_data')
    my_payslip_done = fields.Integer(string='Slip Gaji Selesai', compute='_compute_my_data')
    my_latest_payslip_net = fields.Float(string='Gaji Bersih Terakhir', compute='_compute_my_data')

    # ── My Overtime ──────────────────────────────────────────────────────────
    my_overtime_total = fields.Integer(string='Total Lembur', compute='_compute_my_data')
    my_overtime_pending = fields.Integer(string='Lembur Pending', compute='_compute_my_data')
    my_overtime_approved = fields.Integer(string='Lembur Disetujui', compute='_compute_my_data')
    my_overtime_pay_total = fields.Float(string='Total Upah Lembur', compute='_compute_my_data')

    # ── My Leaves ────────────────────────────────────────────────────────────
    my_leave_total = fields.Integer(string='Total Cuti', compute='_compute_my_data')
    my_leave_pending = fields.Integer(string='Cuti Pending', compute='_compute_my_data')
    my_leave_approved_days = fields.Float(string='Hari Cuti Disetujui', compute='_compute_my_data')

    # ── My Expenses ──────────────────────────────────────────────────────────
    my_expense_total = fields.Integer(string='Total Expense', compute='_compute_my_data')
    my_expense_draft = fields.Integer(string='Expense Draft', compute='_compute_my_data')
    my_expense_amount = fields.Float(string='Total Nominal Expense', compute='_compute_my_data')

    # ── My Attendance ────────────────────────────────────────────────────────
    my_attendance_count = fields.Integer(string='Total Absensi', compute='_compute_my_data')
    my_last_checkin = fields.Datetime(string='Check-in Terakhir', compute='_compute_my_data')
    my_total_work_hours = fields.Float(string='Total Jam Kerja', compute='_compute_my_data')

    # ── My Shift ─────────────────────────────────────────────────────────────
    my_shift_name = fields.Char(string='Shift Saat Ini', compute='_compute_my_data')
    my_shift_hours = fields.Char(string='Jam Kerja', compute='_compute_my_data')
    my_shift_days = fields.Char(string='Hari Kerja', compute='_compute_my_data')

    # ── Trial ────────────────────────────────────────────────────────────────
    trial_days_left = fields.Integer(compute='_compute_trial_info')
    trial_expired = fields.Boolean(compute='_compute_trial_info')

    @api.depends()
    def _compute_trial_info(self):
        for rec in self:
            info = self.env['hr.payslip']._get_trial_info()
            rec.trial_days_left = info['days_left']
            rec.trial_expired = info['expired']

    @api.depends()
    def _compute_my_data(self):
        for rec in self:
            employee = self.env.user.employee_id
            if not employee:
                rec.employee_name = self.env.user.name
                continue

            # Employee info
            rec.employee_name = employee.name
            rec.employee_department = employee.department_id.name if employee.department_id else ''
            rec.employee_job = employee.job_id.name if employee.job_id else ''
            rec.employee_nik = employee.nik or ''
            rec.employee_npwp = employee.npwp or ''
            rec.employee_ptkp = employee.ptkp_status or ''
            rec.employee_bank_name = employee.bank_name or ''
            rec.employee_bank_account = employee.bank_account_number or ''
            rec.employee_join_date = employee.join_date

            # My payslips
            payslips = self.env['hr.payslip'].search([('employee_id', '=', employee.id)])
            rec.my_payslip_count = len(payslips)
            rec.my_payslip_draft = len(payslips.filtered(lambda p: p.state == 'draft'))
            rec.my_payslip_done = len(payslips.filtered(lambda p: p.state == 'done'))
            done_slips = payslips.filtered(lambda p: p.state == 'done').sorted(key=lambda s: s.date_from, reverse=True)
            rec.my_latest_payslip_net = done_slips[0].net_wage if done_slips else 0.0

            # My overtime
            ots = self.env['hr.overtime'].search([('employee_id', '=', employee.id)])
            rec.my_overtime_total = len(ots)
            rec.my_overtime_pending = len(ots.filtered(lambda o: o.state == 'submitted'))
            rec.my_overtime_approved = len(ots.filtered(lambda o: o.state == 'approved'))
            rec.my_overtime_pay_total = sum(ots.filtered(lambda o: o.state == 'approved').mapped('overtime_pay'))

            # My leaves
            leaves = self.env['hr.leave'].search([('employee_id', '=', employee.id)])
            rec.my_leave_total = len(leaves)
            rec.my_leave_pending = len(leaves.filtered(lambda l: l.state == 'confirm'))
            rec.my_leave_approved_days = sum(leaves.filtered(lambda l: l.state == 'validate').mapped('number_of_days'))

            # My expenses (if hr_expense installed)
            has_expense = self.env['ir.module.module'].search_count([
                ('name', '=', 'hr_expense'), ('state', '=', 'installed')
            ])
            if has_expense:
                expenses = self.env['hr.expense'].search([('employee_id', '=', employee.id)])
                rec.my_expense_total = len(expenses)
                rec.my_expense_draft = len(expenses.filtered(lambda e: e.state in ['draft', 'reported']))
                rec.my_expense_amount = sum(expenses.filtered(lambda e: e.state == 'done').mapped('total_amount'))
            else:
                rec.my_expense_total = 0
                rec.my_expense_draft = 0
                rec.my_expense_amount = 0.0

            # My attendance
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id)
            ], order='check_in desc')
            rec.my_attendance_count = len(attendances)
            rec.my_last_checkin = attendances[0].check_in if attendances else False
            rec.my_total_work_hours = sum(attendances.mapped('worked_hours'))

            # My shift — use hr.shift.daily (our actual shift model)
            today = fields.Date.today()
            today_shift = self.env['hr.shift.daily'].search([
                ('employee_id', '=', employee.id),
                ('date', '=', today),
            ], limit=1)
            if today_shift:
                rec.my_shift_name = today_shift.shift_name or ''
                if today_shift.hour_from and today_shift.hour_to:
                    h_from = int(today_shift.hour_from)
                    m_from = int((today_shift.hour_from - h_from) * 60)
                    h_to = int(today_shift.hour_to)
                    m_to = int((today_shift.hour_to - h_to) * 60)
                    rec.my_shift_hours = f'{h_from:02d}:{m_from:02d} - {h_to:02d}:{m_to:02d}'
                else:
                    rec.my_shift_hours = ''
                rec.my_shift_days = today.strftime('%A')
            elif employee.resource_calendar_id:
                rec.my_shift_name = employee.resource_calendar_id.name
                rec.my_shift_hours = ''
                rec.my_shift_days = ''
            else:
                rec.my_shift_name = 'Tidak ada shift'
                rec.my_shift_hours = ''
                rec.my_shift_days = ''

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_open_my_payslips(self):
        employee = self.env.user.employee_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Slip Gaji Saya',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', employee.id)] if employee else [],
        }

    def action_open_my_overtime(self):
        employee = self.env.user.employee_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lembur Saya',
            'res_model': 'hr.overtime',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', employee.id)] if employee else [],
        }

    def action_open_my_leaves(self):
        employee = self.env.user.employee_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cuti Saya',
            'res_model': 'hr.leave',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', employee.id)] if employee else [],
        }

    def action_open_my_expenses(self):
        employee = self.env.user.employee_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expense Saya',
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', employee.id)] if employee else [],
        }

    def action_open_my_attendance(self):
        employee = self.env.user.employee_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Absensi Saya',
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', employee.id)] if employee else [],
        }

    def action_create_overtime(self):
        employee = self.env.user.employee_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Buat Lembur',
            'res_model': 'hr.overtime',
            'view_mode': 'form',
            'context': {
                'default_employee_id': employee.id if employee else False,
            },
        }

    def action_create_leave(self):
        employee = self.env.user.employee_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ajukan Cuti',
            'res_model': 'hr.leave',
            'view_mode': 'form',
            'context': {
                'default_employee_id': employee.id if employee else False,
            },
        }

    def action_create_expense(self):
        employee = self.env.user.employee_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ajukan Expense',
            'res_model': 'hr.expense',
            'view_mode': 'form',
            'context': {
                'default_employee_id': employee.id if employee else False,
            },
        }
