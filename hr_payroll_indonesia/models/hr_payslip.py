# -*- coding: utf-8 -*-
"""
Payslip Model (Standalone)
==========================
Model standalone untuk slip gaji Indonesia.
Digunakan jika modul hr_payroll tidak tersedia.
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Slip Gaji Indonesia'
    _inherit = ['mail.thread', 'trial.mixin']
    _order = 'date_from desc, employee_id'

    name = fields.Char(
        string='Nomor Slip Gaji',
        readonly=True,
        default='/',
        copy=False,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        required=True,
        tracking=True,
    )
    contract_id = fields.Many2one(
        'hr.contract',
        string='Kontrak Aktif',
        related='employee_id.contract_id',
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        related='contract_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        related='contract_id.currency_id',
        store=True,
    )
    date_from = fields.Date(
        string='Tanggal Mulai',
        required=True,
    )
    date_to = fields.Date(
        string='Tanggal Selesai',
        required=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('computed', 'Dihitung'),
            ('done', 'Selesai'),
            ('cancel', 'Dibatalkan'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
    )

    # ── Ringkasan Penghasilan ─────────────────────────────────────────────────
    gaji_pokok = fields.Float(
        string='Gaji Pokok (Rp)',
        compute='_compute_components',
        store=True,
    )
    tunjangan_tetap = fields.Float(
        string='Tunjangan Tetap (Rp)',
        compute='_compute_components',
        store=True,
    )
    tunjangan_tidak_tetap = fields.Float(
        string='Tunjangan Tidak Tetap (Rp)',
        compute='_compute_components',
        store=True,
    )
    total_penghasilan = fields.Float(
        string='Total Penghasilan (Rp)',
        compute='_compute_components',
        store=True,
    )

    # ── Ringkasan PPh 21 ──────────────────────────────────────────────────────
    pph21_ids = fields.One2many(
        'hr.pph21',
        'payslip_id',
        string='Rincian PPh 21',
    )
    pph21_amount = fields.Float(
        string='PPh 21 Bulan Ini (Rp)',
        compute='_compute_pph21_amount',
        store=True,
    )
    pph21_tahunan = fields.Float(
        string='PPh 21 Setahun (Rp)',
        compute='_compute_pph21_amount',
        store=True,
    )
    pph21_pkp = fields.Float(
        string='PKP Setahun (Rp)',
        compute='_compute_pph21_amount',
        store=True,
    )

    # ── Ringkasan BPJS ────────────────────────────────────────────────────────
    bpjs_ids = fields.One2many(
        'hr.bpjs',
        'payslip_id',
        string='Rincian BPJS',
    )
    bpjs_potongan_karyawan = fields.Float(
        string='Total Potongan BPJS Karyawan (Rp)',
        compute='_compute_bpjs_totals',
        store=True,
    )
    bpjs_kontribusi_perusahaan = fields.Float(
        string='Total Kontribusi BPJS Perusahaan (Rp)',
        compute='_compute_bpjs_totals',
        store=True,
    )

    # ── Overtime ──────────────────────────────────────────────────────────────
    overtime_ids = fields.One2many(
        'hr.overtime',
        'payslip_id',
        string='Lembur Periode Ini',
    )
    overtime_total = fields.Float(
        string='Total Upah Lembur (Rp)',
        compute='_compute_overtime_total',
        store=True,
    )
    overtime_count = fields.Integer(
        string='Jumlah Hari Lembur',
        compute='_compute_overtime_total',
        store=True,
    )

    # ── THR ───────────────────────────────────────────────────────────────────
    include_thr = fields.Boolean(
        string='Termasuk THR',
        default=False,
        help='Centang jika slip gaji ini menyertakan THR',
    )
    thr_amount = fields.Float(
        string='Jumlah THR (Rp)',
    )

    # ── Loan (Pinjaman) ──────────────────────────────────────────────────────
    loan_id = fields.Many2one(
        'hr.loan',
        string='Pinjaman',
        readonly=True,
    )
    loan_amount = fields.Float(
        string='Cicilan Pinjaman (Rp)',
    )

    # ── Net Wage ──────────────────────────────────────────────────────────────
    net_wage = fields.Float(
        string='Gaji Bersih (Rp)',
        compute='_compute_net_wage',
        store=True,
    )

    # ── Bank Info (related dari employee) ─────────────────────────────────────
    bank_name = fields.Char(
        string='Nama Bank',
        related='employee_id.bank_name',
        store=True,
    )
    bank_account_number = fields.Char(
        string='No. Rekening',
        related='employee_id.bank_account_number',
        store=True,
    )
    bank_account_name = fields.Char(
        string='Atas Nama Rekening',
        related='employee_id.bank_account_name',
        store=True,
    )

    # ────────────────────────────────────────────────────────────────────────
    # Compute Methods
    # ────────────────────────────────────────────────────────────────────────

    @api.depends('contract_id.wage', 'contract_id.x_tunjangan_tetap',
                 'contract_id.x_tunjangan_tidak_tetap')
    def _compute_components(self):
        for slip in self:
            contract = slip.contract_id
            if contract:
                slip.gaji_pokok = contract.wage or 0.0
                slip.tunjangan_tetap = contract.x_tunjangan_tetap or 0.0
                slip.tunjangan_tidak_tetap = contract.x_tunjangan_tidak_tetap or 0.0
                slip.total_penghasilan = (
                    slip.gaji_pokok + slip.tunjangan_tetap + slip.tunjangan_tidak_tetap
                )
            else:
                slip.gaji_pokok = 0.0
                slip.tunjangan_tetap = 0.0
                slip.tunjangan_tidak_tetap = 0.0
                slip.total_penghasilan = 0.0

    @api.depends('pph21_ids.pph21_final', 'pph21_ids.pph21_tahunan', 'pph21_ids.pkp_tahunan')
    def _compute_pph21_amount(self):
        for slip in self:
            if slip.pph21_ids:
                rec = slip.pph21_ids[0]
                slip.pph21_amount = rec.pph21_final
                slip.pph21_tahunan = rec.pph21_tahunan
                slip.pph21_pkp = rec.pkp_tahunan
            else:
                slip.pph21_amount = 0.0
                slip.pph21_tahunan = 0.0
                slip.pph21_pkp = 0.0

    @api.depends('bpjs_ids.total_potongan_karyawan', 'bpjs_ids.total_kontribusi_perusahaan')
    def _compute_bpjs_totals(self):
        for slip in self:
            if slip.bpjs_ids:
                rec = slip.bpjs_ids[0]
                slip.bpjs_potongan_karyawan = rec.total_potongan_karyawan
                slip.bpjs_kontribusi_perusahaan = rec.total_kontribusi_perusahaan
            else:
                slip.bpjs_potongan_karyawan = 0.0
                slip.bpjs_kontribusi_perusahaan = 0.0

    @api.depends('overtime_ids.overtime_pay', 'overtime_ids.state')
    def _compute_overtime_total(self):
        for slip in self:
            approved_ot = slip.overtime_ids.filtered(lambda o: o.state == 'approved')
            slip.overtime_total = sum(approved_ot.mapped('overtime_pay'))
            slip.overtime_count = len(approved_ot)

    @api.depends('gaji_pokok', 'tunjangan_tetap', 'tunjangan_tidak_tetap',
                 'overtime_total', 'pph21_amount', 'bpjs_potongan_karyawan',
                 'include_thr', 'thr_amount', 'loan_amount')
    def _compute_net_wage(self):
        for slip in self:
            earnings = (
                slip.gaji_pokok
                + slip.tunjangan_tetap
                + slip.tunjangan_tidak_tetap
                + slip.overtime_total
            )
            if slip.include_thr:
                earnings += slip.thr_amount
            deductions = slip.pph21_amount + slip.bpjs_potongan_karyawan + slip.loan_amount
            slip.net_wage = earnings - deductions

    # ────────────────────────────────────────────────────────────────────────
    # Core Computation — "Hitung Gaji"
    # ────────────────────────────────────────────────────────────────────────

    def action_compute(self):
        """
        Hitung PPh 21, BPJS, dan lembur untuk payslip ini.
        Dipanggil dari tombol 'Hitung Gaji' pada form view.
        """
        self._enforce_trial()
        for slip in self:
            if not slip.contract_id:
                raise UserError(
                    f'Karyawan {slip.employee_id.name} tidak memiliki kontrak aktif. '
                    'Silakan buat kontrak terlebih dahulu.'
                )
            if not slip.date_from or not slip.date_to:
                raise UserError('Tanggal mulai dan tanggal selesai harus diisi.')

            contract = slip.contract_id
            emp = slip.employee_id

            # 1. Build lines_dict from contract
            lines_dict = {
                'IDN_BASIC': contract.wage or 0.0,
                'IDN_TUNJ_TETAP': contract.x_tunjangan_tetap or 0.0,
                'IDN_TUNJ_TIDAK_TETAP': contract.x_tunjangan_tidak_tetap or 0.0,
                'IDN_BONUS': 0.0,
                'IDN_THR': slip.thr_amount if slip.include_thr else 0.0,
                'IDN_OVERTIME': 0.0,
            }

            # 2. Link approved overtime for this period
            ot_domain = [
                ('employee_id', '=', emp.id),
                ('state', '=', 'approved'),
                ('overtime_date', '>=', slip.date_from),
                ('overtime_date', '<=', slip.date_to),
            ]
            overtime_records = self.env['hr.overtime'].search(ot_domain)
            for ot in overtime_records:
                ot.write({'payslip_id': slip.id})
            total_overtime = sum(overtime_records.mapped('overtime_pay'))
            lines_dict['IDN_OVERTIME'] = total_overtime

            # 3. Compute BPJS first (we need employee BPJS deductions for PPh 21)
            bpjs_engine = self.env['hr.bpjs']
            bpjs_result = bpjs_engine.compute_for_payslip(slip, lines_dict)

            # Feed BPJS employee deductions back into lines_dict for PPh 21
            lines_dict['IDN_BPJS_TK_JHT_EMP'] = bpjs_result.get('IDN_BPJS_TK_JHT_EMP', 0.0)
            lines_dict['IDN_BPJS_TK_JP_EMP'] = bpjs_result.get('IDN_BPJS_TK_JP_EMP', 0.0)

            # 4. Compute PPh 21
            pph21_engine = self.env['hr.pph21']
            pph21_engine.compute_for_payslip(slip, lines_dict)

            # 5. Recompute stored fields
            slip._compute_components()
            slip._compute_pph21_amount()
            slip._compute_bpjs_totals()
            slip._compute_overtime_total()
            slip._compute_net_wage()

            # 6. Handle loan installment
            loan = self.env['hr.loan'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'running'),
                ('loan_type', '=', 'installment'),
            ], limit=1)
            if loan:
                installment = loan.get_installment_for_payslip(slip.date_from, slip.date_to)
                if installment:
                    slip.loan_id = loan.id
                    slip.loan_amount = installment.amount
                else:
                    slip.loan_id = False
                    slip.loan_amount = 0.0

            # 7. Update state
            slip.state = 'computed'

    # ────────────────────────────────────────────────────────────────────────
    # Actions
    # ────────────────────────────────────────────────────────────────────────

    def action_link_overtime(self):
        """Buka wizard untuk menghubungkan lembur yang approved ke payslip ini."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hubungkan Lembur',
            'res_model': 'hr.overtime',
            'view_mode': 'list',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'approved'),
                ('payslip_id', '=', False),
                ('overtime_date', '>=', self.date_from),
                ('overtime_date', '<=', self.date_to),
            ],
            'context': {'default_payslip_id': self.id},
        }

    def action_view_pph21_detail(self):
        """Buka rincian kalkulasi PPh 21."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rincian PPh 21',
            'res_model': 'hr.pph21',
            'view_mode': 'form',
            'res_id': self.pph21_ids[0].id if self.pph21_ids else False,
            'target': 'new',
        }

    def action_view_bpjs_detail(self):
        """Buka rincian iuran BPJS."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rincian BPJS',
            'res_model': 'hr.bpjs',
            'view_mode': 'form',
            'res_id': self.bpjs_ids[0].id if self.bpjs_ids else False,
            'target': 'new',
        }

    def action_print_bukti_potong(self):
        """Cetak Bukti Potong 1721-A1/A2."""
        return self.env.ref(
            'hr_payroll_indonesia.action_report_bukti_potong'
        ).report_action(self)

    def action_confirm(self):
        """Konfirmasi slip gaji."""
        self._enforce_trial()
        for slip in self:
            if slip.state not in ('computed', 'draft'):
                raise UserError('Slip gaji harus dihitung terlebih dahulu sebelum dikonfirmasi.')
            slip.state = 'done'

    def action_cancel(self):
        """Batalkan slip gaji."""
        for slip in self:
            slip.state = 'cancel'

    def action_reset_draft(self):
        """Reset ke draft."""
        for slip in self:
            slip.state = 'draft'

    # ────────────────────────────────────────────────────────────────────────
    # CRUD
    # ────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        self._enforce_trial()
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self._generate_payslip_number(vals)
        return super().create(vals_list)

    def _generate_payslip_number(self, vals):
        """
        Generate nomor transaksi slip gaji.
        Format: GJ.MM.YYYY/DDD/NNN
        Contoh: GJ.07.2026/SALES/001

        - GJ    = prefix tetap (Gaji)
        - MM    = bulan dari date_from
        - YYYY  = tahun dari date_from
        - DDD   = kode departemen (3-5 karakter)
        - NNN   = nomor urut per bulan per departemen (001, 002, ...)
        """
        date_from = vals.get('date_from')
        employee_id = vals.get('employee_id')

        if not date_from:
            return '/'

        if isinstance(date_from, str):
            from datetime import datetime
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()

        # Get department code
        dept_code = 'DIV'
        if employee_id:
            emp = self.env['hr.employee'].browse(employee_id)
            if emp.department_id and emp.department_id.code:
                dept_code = emp.department_id.code.upper()
            elif emp.department_id:
                # Auto-generate from department name if no code set
                dept_name = emp.department_id.name or 'DIV'
                if isinstance(dept_name, dict):
                    dept_name = dept_name.get('en_US', dept_name.get('id_ID', 'DIV'))
                dept_code = dept_name[:3].upper()

        # Format: GJ.MM.YYYY
        month_str = str(date_from.month).zfill(2)
        year_str = str(date_from.year)
        prefix = f'GJ.{month_str}.{year_str}/{dept_code}/'

        # Count existing payslips for same month + department
        date_from_obj = date_from
        import calendar
        last_day = calendar.monthrange(date_from_obj.year, date_from_obj.month)[1]
        from datetime import date
        date_to_obj = date(date_from_obj.year, date_from_obj.month, last_day)

        existing_count = self.search_count([
            ('date_from', '>=', date_from_obj),
            ('date_to', '<=', date_to_obj),
            ('department_id.code', '=', dept_code),
        ])

        seq = existing_count + 1
        return f'{prefix}{seq:03d}'
