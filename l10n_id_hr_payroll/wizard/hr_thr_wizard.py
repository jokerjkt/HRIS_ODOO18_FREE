# -*- coding: utf-8 -*-
"""
Wizard: Generate THR Massal
============================
Wizard untuk membuat THR sekaligus untuk semua/beberapa karyawan aktif.
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrThrWizard(models.TransientModel):
    _name = 'hr.thr.wizard'
    _description = 'Wizard Generate THR Massal'

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
    thr_date = fields.Date(
        string='Tanggal Pembayaran THR',
        required=True,
        help='Minimal 7 hari sebelum hari raya',
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Departemen',
        help='Kosongkan untuk semua departemen',
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Karyawan Tertentu',
        help='Kosongkan untuk semua karyawan aktif',
    )
    min_tenure_months = fields.Integer(
        string='Minimum Masa Kerja (Bulan)',
        default=1,
        help='Karyawan dengan masa kerja kurang dari ini tidak akan dibuatkan THR',
    )

    # Preview
    preview_count = fields.Integer(
        string='Jumlah Karyawan',
        compute='_compute_preview',
    )
    preview_total = fields.Float(
        string='Estimasi Total THR (Rp)',
        compute='_compute_preview',
    )

    @api.depends('department_ids', 'employee_ids', 'thr_date', 'min_tenure_months')
    def _compute_preview(self):
        for wizard in self:
            employees = wizard._get_eligible_employees()
            wizard.preview_count = len(employees)
            total = 0.0
            for emp in employees:
                join = emp.join_date or wizard.thr_date
                months = (
                    (wizard.thr_date.year - join.year) * 12
                    + (wizard.thr_date.month - join.month)
                )
                proportion = min(months / 12.0, 1.0) if months >= 1 else 0.0
                wage = emp.contract_id.wage if emp.contract_id else 0.0
                total += wage * proportion
            wizard.preview_total = total

    def _get_eligible_employees(self):
        """Ambil karyawan yang eligible untuk THR."""
        domain = [('active', '=', True)]
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))

        employees = self.env['hr.employee'].search(domain)

        # Filter masa kerja minimum
        eligible = self.env['hr.employee']
        for emp in employees:
            if not emp.join_date:
                continue
            months = (
                (self.thr_date.year - emp.join_date.year) * 12
                + (self.thr_date.month - emp.join_date.month)
            )
            if months >= self.min_tenure_months:
                eligible |= emp
        return eligible

    def action_generate_thr(self):
        """Generate record THR untuk semua karyawan eligible."""
        if not self.thr_date:
            raise UserError('Tanggal pembayaran THR harus diisi.')

        employees = self._get_eligible_employees()
        if not employees:
            raise UserError('Tidak ada karyawan yang memenuhi kriteria THR.')

        thr_records = self.env['hr.thr']
        for emp in employees:
            # Cek duplikat
            existing = self.env['hr.thr'].search([
                ('employee_id', '=', emp.id),
                ('year', '=', self.year),
                ('religious_holiday', '=', self.religious_holiday),
                ('state', '!=', 'draft'),
            ], limit=1)
            if existing:
                continue

            thr = self.env['hr.thr'].create({
                'employee_id': emp.id,
                'year': self.year,
                'religious_holiday': self.religious_holiday,
                'thr_date': self.thr_date,
            })
            thr_records |= thr

        if not thr_records:
            raise UserError('Semua karyawan sudah memiliki data THR untuk periode ini.')

        return {
            'type': 'ir.actions.act_window',
            'name': f'THR {self.year} — {dict(self._fields["religious_holiday"].selection).get(self.religious_holiday)}',
            'res_model': 'hr.thr',
            'view_mode': 'list,form',
            'domain': [('id', 'in', thr_records.ids)],
        }
