# -*- coding: utf-8 -*-
"""
e-Bupot — Electronic Withholding Receipt (Bukti Potong Elektronik)
=================================================================
Generates XML for DJP e-Bupot Unifikasi from PPh 21 data.
Formulir 1721-A1 (karyawan tetap) / 1721-A2 (karyawan tidak tetap/ahli).
"""
import json
from odoo import models, fields, api
from odoo.exceptions import UserError


class HrEbupot(models.Model):
    _name = 'hr.ebupot'
    _description = 'e-Bupot Bukti Potong Elektronik'
    _inherit = ['trial.mixin']
    _order = 'year desc, employee_id'

    name = fields.Char(string='No. Bukti Potong', readonly=True, copy=False)
    employee_id = fields.Many2one('hr.employee', string='Karyawan', required=True)
    npwp = fields.Char(string='NPWP', related='employee_id.npwp', store=True)
    nik = fields.Char(string='NIK', related='employee_id.passport_id', store=True)
    year = fields.Integer(string='Tahun', required=True, default=lambda self: fields.Date.today().year)
    form_type = fields.Selection([
        ('1721A1', '1721-A1 (Karyawan Tetap)'),
        ('1721A2', '1721-A2 (Tidak Tetap/Ahli)'),
    ], string='Jenis Formulir', required=True, default='1721A1')
    ptkp_status = fields.Char(string='Status PTKP')
    ptkp_amount = fields.Float(string='PTKP (Rp)')

    # Income
    gaji_pokok = fields.Float(string='Gaji Pokok')
    tunjangan_tetap = fields.Float(string='Tunjangan Tetap')
    tunjangan_lain = fields.Float(string='Tunjangan Tidak Tetap')
    bonus_thr = fields.Float(string='Bonus / THR')
    penghasilan_bruto = fields.Float(string='Penghasilan Bruto')
    biaya_jabatan = fields.Float(string='Biaya Jabatan')
    iuran_pensiun = fields.Float(string='Iuran Pensiun')
    bpjs_tk_jht = fields.Float(string='JHT Karyawan')
    bpjs_tk_jp = fields.Float(string='JP Karyawan')
    penghasilan_neto = fields.Float(string='Penghasilan Neto')
    pkp = fields.Float(string='PKP')

    # Tax
    pph21_gaji = fields.Float(string='PPh 21 Gaji')
    pph21_bonus_thr = fields.Float(string='PPh 21 Bonus/THR')
    pph21_total = fields.Float(string='PPh 21 Total')
    pph21_dipotong = fields.Float(string='PPh 21 Sudah Dipotong')
    pph21_kurang_bayar = fields.Float(string='Kurang Bayar / (Lebih Bayar)')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('exported', 'XML Di-export'),
        ('submitted', 'Terkirim ke DJP'),
        ('confirmed', 'Dikonfirmasi DJP'),
    ], string='Status', default='draft', tracking=True)
    xml_content = fields.Text(string='XML Content')
    submission_date = fields.Datetime(string='Tanggal Kirim')
    djp_reference = fields.Char(string='Referensi DJP')
    error_msg = fields.Text(string='Error')

    sequence_id = fields.Many2one('ir.sequence', string='Sequence')

    @api.model
    def create(self, vals_list):
        self._enforce_trial()
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.ebupot.sequence'
                ) or '/'
        return super().create(vals_list)

    def action_compute_from_payslip(self):
        """Pull data dari hr.pph21 payslip terkait."""
        for rec in self:
            pph21 = self.env['hr.pph21'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('period_year', '=', rec.year),
            ], order='period_year desc, period_month desc')
            if not pph21:
                raise UserError(f'Tidak ada data PPh 21 untuk {rec.employee_id.name} tahun {rec.year}')

            pph_agg = pph21[0]
            rec.write({
                'ptkp_status': pph_agg.ptkp_status,
                'ptkp_amount': pph_agg.ptkp_amount,
                'gaji_pokok': pph_agg.gaji_pokok,
                'tunjangan_tetap': pph_agg.tunjangan_tetap,
                'tunjangan_lain': pph_agg.tunjangan_lain,
                'bonus_thr': pph_agg.bonus_thr,
                'penghasilan_bruto': pph_agg.penghasilan_bruto_tahunan,
                'biaya_jabatan': pph_agg.biaya_jabatan * 12,
                'bpjs_tk_jht': pph_agg.bpjs_tk_jht_emp * 12,
                'bpjs_tk_jp': pph_agg.bpjs_tk_jp_emp * 12,
                'penghasilan_neto': pph_agg.penghasilan_neto,
                'pkp': pph_agg.pkp_tahunan,
                'pph21_gaji': pph_agg.pph21_tahunan,
                'pph21_bonus_thr': pph_agg.pph21_bonus_thr,
                'pph21_total': pph_agg.pph21_tahunan + pph_agg.pph21_bonus_thr,
                'pph21_dipotong': sum(pph21.mapped('pph21_final')),
            })

    def action_generate_xml(self):
        """Generate XML untuk e-Bupot DJP."""
        for rec in self:
            if rec.pph21_total <= 0:
                raise UserError('PPh 21 total harus lebih dari 0.')

            xml_data = self._build_xml_dict(rec)
            rec.xml_content = json.dumps(xml_data, indent=2, ensure_ascii=False)
            rec.state = 'exported'

    def _build_xml_dict(self, rec):
        """Build dict sesuai format e-Bupot Unifikasi DJP."""
        emp = rec.employee_id
        return {
            'NPWP_PEMOTONG': emp.company_id.npwp or '',
            'NAMA_PEMOTONG': emp.company_id.name or '',
            'NPWP_PENERIMA': rec.npwp or '',
            'NAMA_PENERIMA': emp.name or '',
            'NIK_PENERIMA': rec.nik or '',
            'ALAMAT_PENERIMA': emp.address_home_id.name if emp.address_home_id else '',
            'STATUS_PTKP': rec.ptkp_status or '',
            'JUMLAH_ORG_TANGGUNG': int(rec.ptkp_status.split('/')[-1]) if rec.ptkp_status and '/' in rec.ptkp_status else 0,
            'MASA_PAJAK': f'{rec.year}-01 s.d. {rec.year}-12',
            'TAHUN_PAJAK': str(rec.year),
            'KODE_PAJAK': '411128',
            'JENIS_BUKTI_POTONG': '1721-A1' if rec.form_type == '1721A1' else '1721-A2',
            'JUMLAH_BRUTO': rec.penghasilan_bruto,
            'JUMLAH_PENGURANG': rec.biaya_jabatan + rec.iuran_pensiun + rec.bpjs_tk_jht + rec.bpjs_tk_jp,
            'PKP': rec.pkp,
            'PPh_21_TERUTANG': rec.pph21_total,
            'PPh_21_DIPOTONG': rec.pph21_dipotong,
            'PPh_21_KURANG_BAYAR': rec.pph21_total - rec.pph21_dipotong,
        }

    def action_export(self):
        """Download XML file."""
        self.ensure_one()
        if not self.xml_content:
            self.action_generate_xml()
        return {
            'type': 'ir.actions.act_window',
            'name': f'e-Bupot {self.name}',
            'res_model': 'hr.ebupot',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_submit_to_djp(self):
        """Submit ke DJP API (placeholder — membutuhkan konfigurasi API)."""
        for rec in self:
            if not rec.xml_content:
                rec.action_generate_xml()
            config = self.env['hr.djp.api.config'].search([('is_active', '=', True)], limit=1)
            if not config:
                raise UserError(
                    'Konfigurasi DJP API belum diatur.\n'
                    'Silakan hubungi vendor untuk aktivasi e-Filing.\n'
                    '📧 susilo.cdv@gmail.com'
                )
            rec.submission_date = fields.Datetime.now()
            rec.state = 'submitted'
