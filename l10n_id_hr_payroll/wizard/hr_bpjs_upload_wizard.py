# -*- coding: utf-8 -*-
"""
BPJS Upload Wizard
==================
Wizard untuk generate CSV upload ke BPJS SPT Management.
"""
import base64
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrBpjsUploadWizard(models.TransientModel):
    _name = 'hr.bpjs.upload.wizard'
    _description = 'Wizard Upload BPJS'

    service_type = fields.Selection([
        ('tk', 'BPJS Ketenagakerjaan'),
        ('kes', 'BPJS Kesehatan'),
    ], string='Jenis Layanan', required=True, default='tk')
    period_month = fields.Integer(string='Bulan', required=True,
                                  default=lambda self: fields.Date.today().month)
    period_year = fields.Integer(string='Tahun', required=True,
                                 default=lambda self: fields.Date.today().year)
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Karyawan',
        help='Kosongkan untuk semua karyawan aktif',
    )

    # Preview
    preview_count = fields.Integer(string='Jumlah Karyawan', compute='_compute_preview')
    preview_total = fields.Float(string='Total Iuran', compute='_compute_preview')

    @api.depends('period_month', 'period_year', 'employee_ids')
    def _compute_preview(self):
        for wiz in self:
            lines = wiz._get_payslip_lines()
            wiz.preview_count = len(lines)
            wiz.preview_total = sum(l.get('total', 0) for l in lines)

    def _get_payslip_lines(self):
        """Ambil data BPJS dari payslip."""
        self.ensure_one()
        domain = [
            ('date_from.month', '=', self.period_month),
            ('date_from.year', '=', self.period_year),
            ('state', 'in', ('computed', 'done')),
        ]
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)
        lines = []
        for slip in payslips:
            emp = slip.employee_id
            if not emp:
                continue

            bpjs_detail = self.env['hr.bpjs'].search([
                ('payslip_id', '=', slip.id),
            ], limit=1)

            if self.service_type == 'tk':
                jkk = bpjs_detail.jkk_comp if bpjs_detail else 0.0
                jkm = bpjs_detail.jkm_comp if bpjs_detail else 0.0
                jht_emp = bpjs_detail.jht_emp if bpjs_detail else 0.0
                jht_comp = bpjs_detail.jht_comp if bpjs_detail else 0.0
                jp_emp = bpjs_detail.jp_emp if bpjs_detail else 0.0
                jp_comp = bpjs_detail.jp_comp if bpjs_detail else 0.0
                total = jkk + jkm + jht_emp + jht_comp + jp_emp + jp_comp
                lines.append({
                    'employee_id': emp.id,
                    'bpjs_no': emp.bpjs_tk_no or '',
                    'wage_base': bpjs_detail.upah_dasar if bpjs_detail else 0.0,
                    'jkk': jkk, 'jkm': jkm,
                    'jht_emp': jht_emp, 'jht_comp': jht_comp,
                    'jp_emp': jp_emp, 'jp_comp': jp_comp,
                    'total': total,
                })
            else:
                kes_emp = bpjs_detail.bpjs_kes_emp if bpjs_detail else 0.0
                kes_comp = bpjs_detail.bpjs_kes_comp if bpjs_detail else 0.0
                total = kes_emp + kes_comp
                lines.append({
                    'employee_id': emp.id,
                    'bpjs_no': emp.bpjs_kes_no or '',
                    'wage_base': bpjs_detail.upah_kes_base if bpjs_detail else 0.0,
                    'bpjs_kes_emp': kes_emp,
                    'bpjs_kes_comp': kes_comp,
                    'total': total,
                })
        return lines

    def action_generate_csv(self):
        """Generate CSV file."""
        self.ensure_one()
        lines = self._get_payslip_lines()
        if not lines:
            raise UserError('Tidak ada data untuk periode ini.')

        # Create submission record
        submission = self.env['hr.bpjs.submission'].create({
            'service_type': self.service_type,
            'period_month': self.period_month,
            'period_year': self.period_year,
        })

        for line_data in lines:
            self.env['hr.bpjs.submission.line'].create({
                'submission_id': submission.id,
                'employee_id': line_data['employee_id'],
                'bpjs_no': line_data['bpjs_no'],
                'wage_base': line_data['wage_base'],
                'jkk': line_data.get('jkk', 0),
                'jkm': line_data.get('jkm', 0),
                'jht_emp': line_data.get('jht_emp', 0),
                'jht_comp': line_data.get('jht_comp', 0),
                'jp_emp': line_data.get('jp_emp', 0),
                'jp_comp': line_data.get('jp_comp', 0),
                'bpjs_kes_emp': line_data.get('bpjs_kes_emp', 0),
                'bpjs_kes_comp': line_data.get('bpjs_kes_comp', 0),
            })

        submission.action_generate_csv()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Submission BPJS',
            'res_model': 'hr.bpjs.submission',
            'res_id': submission.id,
            'view_mode': 'form',
            'target': 'current',
        }
