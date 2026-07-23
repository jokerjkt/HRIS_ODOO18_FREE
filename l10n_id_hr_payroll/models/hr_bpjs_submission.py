# -*- coding: utf-8 -*-
"""
BPJS Submission Tracking
========================
Tracks BPJS contribution submissions (TK & Kes).
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrBpjsSubmission(models.Model):
    _name = 'hr.bpjs.submission'
    _description = 'Submission BPJS'
    _inherit = ['trial.mixin']
    _order = 'period_year desc, period_month desc'

    name = fields.Char(string='No. Submission', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Perusahaan',
                                  default=lambda self: self.env.company, required=True)
    service_type = fields.Selection([
        ('tk', 'BPJS Ketenagakerjaan'),
        ('kes', 'BPJS Kesehatan'),
    ], string='Jenis Layanan', required=True)
    period_month = fields.Integer(string='Bulan', required=True)
    period_year = fields.Integer(string='Tahun', required=True)
    line_ids = fields.One2many('hr.bpjs.submission.line', 'submission_id', string='Detail')
    total_amount = fields.Float(string='Total Iuran', compute='_compute_total', store=True)
    total_employee = fields.Integer(string='Jumlah Karyawan', compute='_compute_total', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Terkirim'),
        ('confirmed', 'Dikonfirmasi'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True)
    submission_date = fields.Datetime(string='Tanggal Kirim')
    bpjs_reference = fields.Char(string='Referensi BPJS')
    response_data = fields.Text(string='Response')
    error_msg = fields.Text(string='Error')
    csv_file = fields.Binary(string='File CSV')
    csv_filename = fields.Char(string='Nama File CSV')

    @api.depends('line_ids')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('total_iuran'))
            rec.total_employee = len(rec.line_ids)

    @api.model
    def create(self, vals_list):
        self._enforce_trial()
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                service = vals.get('service_type', 'tk').upper()
                month = vals.get('period_month', 0)
                year = vals.get('period_year', 0)
                vals['name'] = f'BPJS-{service}-{year:04d}-{month:02d}'
        return super().create(vals_list)

    def action_generate_from_payslip(self):
        """Generate submission lines dari data payslip bulan ini."""
        for rec in self:
            if rec.line_ids:
                raise UserError('Data sudah ada. Hapus dulu jika ingin regenerate.')

            payslips = self.env['hr.payslip'].search([
                ('date_from.month', '=', rec.period_month),
                ('date_from.year', '=', rec.period_year),
                ('state', 'in', ('computed', 'done')),
            ])

            if not payslips:
                raise UserError('Tidak ada slip gaji untuk periode ini.')

            for slip in payslips:
                if not slip.employee_id:
                    continue

                emp = slip.employee_id
                bpjs_detail = self.env['hr.bpjs'].search([
                    ('payslip_id', '=', slip.id),
                ], limit=1)

                if rec.service_type == 'tk':
                    self.env['hr.bpjs.submission.line'].create({
                        'submission_id': rec.id,
                        'employee_id': emp.id,
                        'bpjs_no': emp.bpjs_tk_no or '',
                        'wage_base': bpjs_detail.upah_dasar if bpjs_detail else 0.0,
                        'jkk': bpjs_detail.jkk_comp if bpjs_detail else 0.0,
                        'jkm': bpjs_detail.jkm_comp if bpjs_detail else 0.0,
                        'jht_emp': bpjs_detail.jht_emp if bpjs_detail else 0.0,
                        'jht_comp': bpjs_detail.jht_comp if bpjs_detail else 0.0,
                        'jp_emp': bpjs_detail.jp_emp if bpjs_detail else 0.0,
                        'jp_comp': bpjs_detail.jp_comp if bpjs_detail else 0.0,
                    })
                else:  # kes
                    self.env['hr.bpjs.submission.line'].create({
                        'submission_id': rec.id,
                        'employee_id': emp.id,
                        'bpjs_no': emp.bpjs_kes_no or '',
                        'wage_base': bpjs_detail.upah_kes_base if bpjs_detail else 0.0,
                        'bpjs_kes_emp': bpjs_detail.bpjs_kes_emp if bpjs_detail else 0.0,
                        'bpjs_kes_comp': bpjs_detail.bpjs_kes_comp if bpjs_detail else 0.0,
                    })

    def action_generate_csv(self):
        """Generate CSV file untuk upload ke BPJS SPT Management."""
        for rec in self:
            if not rec.line_ids:
                raise UserError('Generate data terlebih dahulu.')

            if rec.service_type == 'tk':
                csv_content = self._generate_csv_tk(rec)
                filename = f'BPJS_TK_{rec.period_year:04d}_{rec.period_month:02d}.csv'
            else:
                csv_content = self._generate_csv_kes(rec)
                filename = f'BPJS_KES_{rec.period_year:04d}_{rec.period_month:02d}.csv'

            import base64
            rec.csv_file = base64.b64encode(csv_content.encode('utf-8'))
            rec.csv_filename = filename

    def _generate_csv_tk(self, rec):
        """Generate CSV format untuk BPJS TK SPT Management."""
        lines = ['No,Nama,No BPJS TK,Upah Dasar,JKK,JKM,JHT Karyawan,JHT Perusahaan,JP Karyawan,JP Perusahaan,Total']
        for i, line in enumerate(rec.line_ids, 1):
            total = line.jkk + line.jkm + line.jht_emp + line.jht_comp + line.jp_emp + line.jp_comp
            lines.append(
                f'{i},{line.employee_id.name},{line.bpjs_no},'
                f'{line.wage_base:.0f},{line.jkk:.0f},{line.jkm:.0f},'
                f'{line.jht_emp:.0f},{line.jht_comp:.0f},'
                f'{line.jp_emp:.0f},{line.jp_comp:.0f},{total:.0f}'
            )
        return '\n'.join(lines)

    def _generate_csv_kes(self, rec):
        """Generate CSV format untuk BPJS Kes SPT Management."""
        lines = ['No,Nama,No Peserta,Upah Dasar,Iuran Karyawan (1%),Iuran Perusahaan (4%),Total']
        for i, line in enumerate(rec.line_ids, 1):
            total = line.bpjs_kes_emp + line.bpjs_kes_comp
            lines.append(
                f'{i},{line.employee_id.name},{line.bpjs_no},'
                f'{line.wage_base:.0f},{line.bpjs_kes_emp:.0f},'
                f'{line.bpjs_kes_comp:.0f},{total:.0f}'
            )
        return '\n'.join(lines)

    def action_submit_api(self):
        """Submit via BPJS API (jika sudah dikonfigurasi)."""
        for rec in self:
            if not rec.line_ids:
                raise UserError('Data kosong.')

            if rec.service_type == 'tk':
                connector = self.env['hr.bpjs.tk.connector']
            else:
                connector = self.env['hr.bpjs.kes.connector']

            data = []
            for line in rec.line_ids:
                row = {
                    'nik': line.employee_id.passport_id or '',
                    'no_bpjs': line.bpjs_no,
                    'nama': line.employee_id.name,
                    'upah': line.wage_base,
                }
                if rec.service_type == 'tk':
                    row.update({
                        'jkk': line.jkk,
                        'jkm': line.jkm,
                        'jht_emp': line.jht_emp,
                        'jht_comp': line.jht_comp,
                        'jp_emp': line.jp_emp,
                        'jp_comp': line.jp_comp,
                    })
                else:
                    row.update({
                        'bpjs_kes_emp': line.bpjs_kes_emp,
                        'bpjs_kes_comp': line.bpjs_kes_comp,
                    })
                data.append(row)

            result = connector.submit_contribution(data)
            rec.submission_date = fields.Datetime.now()
            rec.response_data = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
            if result.get('error'):
                rec.state = 'error'
                rec.error_msg = result['error']
            else:
                rec.state = 'submitted'

    def action_confirm(self):
        for rec in self:
            if rec.state not in ('submitted', 'draft'):
                raise UserError('Status tidak valid untuk konfirmasi.')
            rec.state = 'confirmed'


class HrBpjsSubmissionLine(models.Model):
    _name = 'hr.bpjs.submission.line'
    _description = 'Detail Submission BPJS'

    submission_id = fields.Many2one('hr.bpjs.submission', string='Submission',
                                    required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Karyawan', required=True)
    bpjs_no = fields.Char(string='No. BPJS')
    wage_base = fields.Float(string='Upah Dasar')

    # BPJS TK
    jkk = fields.Float(string='JKK (Perusahaan)')
    jkm = fields.Float(string='JKM (Perusahaan)')
    jht_emp = fields.Float(string='JHT Karyawan')
    jht_comp = fields.Float(string='JHT Perusahaan')
    jp_emp = fields.Float(string='JP Karyawan')
    jp_comp = fields.Float(string='JP Perusahaan')

    # BPJS Kes
    bpjs_kes_emp = fields.Float(string='BPJS Kes Karyawan')
    bpjs_kes_comp = fields.Float(string='BPJS Kes Perusahaan')

    total_iuran = fields.Float(string='Total Iuran', compute='_compute_total', store=True)

    @api.depends('jkk', 'jkm', 'jht_emp', 'jht_comp', 'jp_emp', 'jp_comp', 'bpjs_kes_emp', 'bpjs_kes_comp')
    def _compute_total(self):
        for rec in self:
            rec.total_iuran = (rec.jkk + rec.jkm + rec.jht_emp + rec.jht_comp +
                               rec.jp_emp + rec.jp_comp + rec.bpjs_kes_emp + rec.bpjs_kes_comp)
