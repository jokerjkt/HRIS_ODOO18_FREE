# -*- coding: utf-8 -*-
"""
Modul Lembur (Overtime)
========================
Pencatatan manual kegiatan lembur dengan workflow validasi atasan.

Flow:
    Karyawan buat request → Submit → Manager review → Approve / Reject
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrOvertime(models.Model):
    _name = 'hr.overtime'
    _description = 'Pengajuan Lembur'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trial.mixin']
    _order = 'overtime_date desc, id desc'
    _rec_name = 'display_name'

    # ── Identitas ─────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Nomor Pengajuan',
        readonly=True,
        default='/',
        copy=False,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Departemen',
        related='employee_id.department_id',
        store=True,
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Jabatan',
        related='employee_id.job_id',
        store=True,
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Atasan',
        related='employee_id.parent_id',
        store=True,
        tracking=True,
    )

    # ── Waktu Lembur ──────────────────────────────────────────────────────────
    overtime_date = fields.Date(
        string='Tanggal Lembur',
        required=True,
        tracking=True,
    )
    start_time = fields.Float(
        string='Jam Mulai',
        required=True,
        help='Contoh: 17.5 = 17:30',
    )
    end_time = fields.Float(
        string='Jam Selesai',
        required=True,
    )
    duration = fields.Float(
        string='Durasi (Jam)',
        compute='_compute_duration',
        store=True,
        help='Durasi lembur dalam jam',
    )

    # ── Tipe & Multiplier ─────────────────────────────────────────────────────
    overtime_type = fields.Selection(
        selection=[
            ('weekday',  'Hari Kerja'),
            ('weekend',  'Hari Libur / Sabtu-Minggu'),
            ('holiday',  'Hari Besar Nasional'),
        ],
        string='Jenis Hari',
        required=True,
        default='weekday',
        tracking=True,
    )
    multiplier_first = fields.Float(
        string='Faktor Jam Pertama',
        compute='_compute_multiplier',
        store=True,
        help='Faktor pengali upah untuk jam lembur pertama',
    )
    multiplier_next = fields.Float(
        string='Faktor Jam Berikutnya',
        compute='_compute_multiplier',
        store=True,
        help='Faktor pengali upah untuk jam lembur berikutnya',
    )
    overtime_pay = fields.Float(
        string='Upah Lembur (Rp)',
        compute='_compute_overtime_pay',
        store=True,
        help='Estimasi upah lembur berdasarkan gaji kontrak',
    )

    # ── Deskripsi & Alasan ────────────────────────────────────────────────────
    reason = fields.Char(
        string='Alasan Lembur',
        required=True,
        help='Alasan singkat mengapa lembur diperlukan',
    )
    activity_description = fields.Text(
        string='Deskripsi Kegiatan Lembur',
        required=True,
        help='Uraian detail kegiatan yang dilakukan selama lembur. '
             'Wajib diisi dan akan digunakan sebagai dasar persetujuan atasan.',
    )
    result_output = fields.Text(
        string='Output / Hasil Kegiatan',
        help='Hasil atau output nyata yang dicapai selama lembur',
    )
    notes = fields.Text(
        string='Catatan Tambahan',
    )

    # ── Workflow ──────────────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft',    'Draft'),
            ('submitted', 'Menunggu Persetujuan'),
            ('approved', 'Disetujui'),
            ('rejected', 'Ditolak'),
            ('cancelled', 'Dibatalkan'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
    )
    approved_date = fields.Datetime(
        string='Tanggal Persetujuan',
        readonly=True,
        copy=False,
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Disetujui Oleh',
        readonly=True,
        copy=False,
    )
    reject_reason = fields.Text(
        string='Alasan Penolakan',
        copy=False,
    )

    # ── Payslip Link ──────────────────────────────────────────────────────────
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Slip Gaji',
        readonly=True,
        copy=False,
        help='Diisi otomatis saat lembur telah dimasukkan ke payslip',
    )
    is_included_payslip = fields.Boolean(
        string='Sudah di Payslip',
        compute='_compute_is_included_payslip',
        store=True,
    )

    # ── Computed ──────────────────────────────────────────────────────────────
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )

    # ────────────────────────────────────────────────────────────────────────
    # Compute Methods
    # ────────────────────────────────────────────────────────────────────────

    @api.depends('employee_id', 'overtime_date')
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or '—'
            date = rec.overtime_date or '—'
            rec.display_name = f'Lembur {emp} — {date}'

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.end_time > rec.start_time:
                rec.duration = rec.end_time - rec.start_time
            elif rec.end_time < rec.start_time:
                # Lembur lewat tengah malam
                rec.duration = (24 - rec.start_time) + rec.end_time
            else:
                rec.duration = 0.0

    @api.depends('overtime_type')
    def _compute_multiplier(self):
        """
        Sesuai Permenaker No. 5 Tahun 2023:
        - Hari Kerja  : jam 1 = 1.5x, jam 2+ = 2x
        - Hari Libur  : jam 1-8 = 2x, jam 9 = 3x, jam 10+ = 4x
        - Hari Besar  : sama dengan Hari Libur
        """
        for rec in self:
            if rec.overtime_type == 'weekday':
                rec.multiplier_first = 1.5
                rec.multiplier_next = 2.0
            else:
                rec.multiplier_first = 2.0
                rec.multiplier_next = 3.0

    @api.depends('duration', 'multiplier_first', 'multiplier_next', 'employee_id')
    def _compute_overtime_pay(self):
        for rec in self:
            if not rec.employee_id or not rec.duration:
                rec.overtime_pay = 0.0
                continue
            # Upah sejam = gaji sebulan / 173
            contract = rec.employee_id.contract_id
            monthly_wage = contract.wage if contract else 0.0
            hourly_rate = monthly_wage / 173.0

            if rec.duration <= 1:
                pay = rec.duration * hourly_rate * rec.multiplier_first
            else:
                pay = (1 * hourly_rate * rec.multiplier_first) + \
                      ((rec.duration - 1) * hourly_rate * rec.multiplier_next)
            rec.overtime_pay = pay

    @api.depends('payslip_id')
    def _compute_is_included_payslip(self):
        for rec in self:
            rec.is_included_payslip = bool(rec.payslip_id)

    # ────────────────────────────────────────────────────────────────────────
    # Constraints
    # ────────────────────────────────────────────────────────────────────────

    @api.constrains('start_time', 'end_time')
    def _check_time(self):
        for rec in self:
            if rec.start_time == rec.end_time:
                raise ValidationError('Jam mulai dan jam selesai tidak boleh sama.')

    @api.constrains('activity_description')
    def _check_activity_description(self):
        for rec in self:
            if rec.state not in ('draft',) and not rec.activity_description:
                raise ValidationError('Deskripsi kegiatan lembur wajib diisi sebelum submit.')

    @api.constrains('overtime_date', 'employee_id')
    def _check_duplicate(self):
        for rec in self:
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('overtime_date', '=', rec.overtime_date),
                ('state', 'not in', ('cancelled', 'rejected')),
                ('id', '!=', rec.id),
            ]
            if self.search(domain, limit=1):
                raise ValidationError(
                    f'Karyawan {rec.employee_id.name} sudah memiliki pengajuan lembur '
                    f'pada tanggal {rec.overtime_date}.'
                )

    # ────────────────────────────────────────────────────────────────────────
    # CRUD Overrides
    # ────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        self._enforce_trial()
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.overtime') or '/'
        return super().create(vals_list)

    # ────────────────────────────────────────────────────────────────────────
    # Action Methods (Workflow Buttons)
    # ────────────────────────────────────────────────────────────────────────

    def action_submit(self):
        """Karyawan submit pengajuan lembur ke atasan."""
        self._enforce_trial()
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Hanya pengajuan dengan status Draft yang bisa disubmit.')
            if not rec.activity_description:
                raise UserError('Silakan isi Deskripsi Kegiatan Lembur sebelum submit.')
            rec.state = 'submitted'
            # Kirim notifikasi ke atasan
            rec._notify_manager_for_approval()

    def action_approve(self):
        """Manager menyetujui lembur."""
        for rec in self:
            if rec.state != 'submitted':
                raise UserError('Hanya pengajuan yang sudah disubmit yang dapat disetujui.')
            rec.write({
                'state': 'approved',
                'approved_date': fields.Datetime.now(),
                'approved_by': self.env.user.id,
            })
            rec.message_post(
                body=f'✅ Lembur disetujui oleh {self.env.user.name}.',
                subtype_xmlid='mail.mt_note',
            )
            rec._notify_employee_result('approved')

    def action_reject(self):
        """Manager menolak lembur — buka wizard input alasan."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Alasan Penolakan',
            'res_model': 'hr.overtime.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_overtime_id': self.id},
        }

    def action_cancel(self):
        """Karyawan membatalkan pengajuan."""
        for rec in self:
            if rec.state not in ('draft', 'submitted'):
                raise UserError('Hanya pengajuan Draft atau Submitted yang bisa dibatalkan.')
            if rec.is_included_payslip:
                raise UserError('Lembur ini sudah masuk ke payslip dan tidak dapat dibatalkan.')
            rec.state = 'cancelled'

    def action_reset_draft(self):
        """Reset ke draft (jika ditolak atau dibatalkan)."""
        for rec in self:
            if rec.state not in ('rejected', 'cancelled'):
                raise UserError('Hanya pengajuan yang ditolak atau dibatalkan yang bisa direset.')
            rec.state = 'draft'

    # ────────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ────────────────────────────────────────────────────────────────────────

    def _notify_manager_for_approval(self):
        """Kirim notifikasi email ke atasan untuk review lembur."""
        for rec in self:
            if not rec.manager_id or not rec.manager_id.work_email:
                continue
            template = self.env.ref(
                'l10n_id_hr_payroll.email_template_overtime_approval',
                raise_if_not_found=False,
            )
            if template:
                template.send_mail(rec.id, force_send=True)
            else:
                rec.message_post(
                    body=_(
                        'Pengajuan lembur dari <b>%(emp)s</b> pada tanggal <b>%(date)s</b> '
                        'memerlukan persetujuan Anda.<br/>'
                        '<b>Kegiatan:</b> %(activity)s'
                    ) % {
                        'emp': rec.employee_id.name,
                        'date': rec.overtime_date,
                        'activity': rec.activity_description or '—',
                    },
                    partner_ids=[rec.manager_id.user_id.partner_id.id]
                    if rec.manager_id.user_id else [],
                )

    def _notify_employee_result(self, result):
        """Notifikasi hasil approval ke karyawan."""
        for rec in self:
            status_text = 'disetujui ✅' if result == 'approved' else 'ditolak ❌'
            rec.message_post(
                body=f'Pengajuan lembur Anda pada tanggal {rec.overtime_date} telah {status_text}.',
                partner_ids=[rec.employee_id.user_id.partner_id.id]
                if rec.employee_id.user_id else [],
                subtype_xmlid='mail.mt_note',
            )

    # ────────────────────────────────────────────────────────────────────────
    # Utility
    # ────────────────────────────────────────────────────────────────────────

    def _format_time(self, float_time):
        """Convert float time (e.g. 17.5) ke string HH:MM."""
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f'{hours:02d}:{minutes:02d}'


class HrOvertimeRejectWizard(models.TransientModel):
    """Wizard untuk input alasan penolakan lembur."""
    _name = 'hr.overtime.reject.wizard'
    _description = 'Alasan Penolakan Lembur'

    overtime_id = fields.Many2one('hr.overtime', string='Lembur', required=True)
    reject_reason = fields.Text(string='Alasan Penolakan', required=True)

    def action_confirm_reject(self):
        self.overtime_id.write({
            'state': 'rejected',
            'reject_reason': self.reject_reason,
        })
        self.overtime_id.message_post(
            body=f'❌ Lembur ditolak. Alasan: {self.reject_reason}',
            subtype_xmlid='mail.mt_note',
        )
        self.overtime_id._notify_employee_result('rejected')
