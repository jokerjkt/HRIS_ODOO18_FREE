# -*- coding: utf-8 -*-
"""
Wizard: Buat Slip Gaji Massal
==============================
Wizard untuk membuat slip gaji sekaligus untuk semua/beberapa karyawan aktif
dalam satu periode.
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrPayslipGenerateWizard(models.TransientModel):
    _name = 'hr.payslip.generate.wizard'
    _description = 'Wizard Buat Slip Gaji Massal'

    date_from = fields.Date(
        string='Tanggal Mulai',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    date_to = fields.Date(
        string='Tanggal Akhir',
        required=True,
        default=lambda self: fields.Date.today(),
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
    auto_compute = fields.Boolean(
        string='Langsung Hitung Gaji',
        default=True,
        help='Jika dicentang, slip gaji akan langsung dihitung (PPh 21, BPJS, Lembur)',
    )

    # Preview
    preview_count = fields.Integer(
        string='Jumlah Karyawan',
        compute='_compute_preview',
    )
    preview_total = fields.Float(
        string='Estimasi Total Gaji Bersih (Rp)',
        compute='_compute_preview',
    )
    existing_count = fields.Integer(
        string='Sudah Ada',
        compute='_compute_preview',
    )

    @api.depends('date_from', 'date_to', 'department_ids', 'employee_ids')
    def _compute_preview(self):
        for wizard in self:
            employees = wizard._get_eligible_employees()
            wizard.preview_count = len(employees)

            # Hitung existing
            if wizard.date_from and wizard.date_to:
                existing_domain = [
                    ('date_from', '=', wizard.date_from),
                    ('date_to', '=', wizard.date_to),
                ]
                if employees:
                    existing_domain.append(
                        ('employee_id', 'in', employees.ids)
                    )
                wizard.existing_count = self.env['hr.payslip'].search_count(
                    existing_domain
                )
            else:
                wizard.existing_count = 0

            # Estimasi gaji bersih
            total = 0.0
            for emp in employees:
                if emp.contract_id:
                    total += emp.contract_id.wage or 0.0
            wizard.preview_total = total

    def _get_eligible_employees(self):
        """Ambil karyawan yang eligible untuk slip gaji."""
        domain = [
            ('active', '=', True),
            ('contract_id', '!=', False),
        ]
        if self.department_ids:
            domain.append(
                ('department_id', 'in', self.department_ids.ids)
            )
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))
        return self.env['hr.employee'].search(domain)

    def action_generate_payslips(self):
        """Buat slip gaji massal."""
        self.env['hr.payslip']._enforce_trial()
        if not self.date_from or not self.date_to:
            raise UserError('Periode tanggal harus diisi.')
        if self.date_from > self.date_to:
            raise UserError(
                'Tanggal mulai tidak boleh lebih besar dari tanggal akhir.'
            )

        employees = self._get_eligible_employees()
        if not employees:
            raise UserError(
                'Tidak ada karyawan yang memenuhi kriteria.\n'
                'Pastikan karyawan aktif memiliki kontrak aktif.'
            )

        payslip_records = self.env['hr.payslip']
        skipped = 0

        for emp in employees:
            # Cek duplikat
            existing = self.env['hr.payslip'].search([
                ('employee_id', '=', emp.id),
                ('date_from', '=', self.date_from),
                ('date_to', '=', self.date_to),
            ], limit=1)
            if existing:
                skipped += 1
                continue

            # Buat slip gaji
            slip = self.env['hr.payslip'].create({
                'employee_id': emp.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
            })

            # Auto compute jika diminta
            if self.auto_compute:
                try:
                    slip.action_compute()
                except Exception:
                    pass  # Skip jika compute gagal (misal: kontrak tidak lengkap)

            payslip_records |= slip

        if not payslip_records:
            raise UserError(
                f'Semua karyawan ({skipped} orang) sudah memiliki '
                f'slip gaji untuk periode ini.'
            )

        # Return action ke daftar slip gaji
        return {
            'type': 'ir.actions.act_window',
            'name': f'Slip Gaji {self.date_from.strftime("%B %Y")}',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payslip_records.ids)],
            'context': {'create': False},
            'help': (
                f'<p class="o_view_nocontent_smiling_face">'
                f'Dibuat {len(payslip_records)} slip gaji'
                f'{f", {skipped} dilewati (sudah ada)" if skipped else ""}'
                f'</p>'
            ),
        }
