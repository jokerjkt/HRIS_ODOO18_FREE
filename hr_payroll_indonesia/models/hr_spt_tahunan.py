# -*- coding: utf-8 -*-
"""
SPT Tahunan — Annual Tax Return Aggregator
==========================================
Aggregates 12 months of PPh 21 data per employee per year.
Generates XML for SPT Masa PPh Unifikasi.
"""
import base64
import xml.etree.ElementTree as ET
from xml.dom import minidom

from odoo import models, fields, api
from odoo.exceptions import UserError


class HrSptTahunan(models.Model):
    _name = 'hr.spt.tahunan'
    _description = 'SPT Tahunan PPh 21'
    _inherit = ['trial.mixin']
    _order = 'year desc, employee_id'
    _rec_name = 'display_name'

    name = fields.Char(string='No. SPT', readonly=True, copy=False)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Karyawan', required=True)
    year = fields.Integer(string='Tahun Pajak', required=True,
                          default=lambda self: fields.Date.today().year)
    pph21_ids = fields.One2many('hr.pph21', 'employee_id', string='Detail PPh 21')

    # Aggregated income
    total_gaji_pokok = fields.Float(string='Total Gaji Pokok')
    total_tunj_tetap = fields.Float(string='Total Tunjangan Tetap')
    total_tunj_lain = fields.Float(string='Total Tunjangan Tidak Tetap')
    total_bonus_thr = fields.Float(string='Total Bonus/THR')
    total_bruto = fields.Float(string='Total Penghasilan Bruto')
    total_pengurang = fields.Float(string='Total Pengurang')
    total_bruto_12_bulan = fields.Float(string='Bruto 12 Bulan (Tanpa THR)')

    # BPJS
    total_bpjs_tk = fields.Float(string='Total BPJS TK (Karyawan)')
    total_bpjs_kes = fields.Float(string='Total BPJS Kes (Karyawan)')

    # Tax
    ptkp_status = fields.Char(string='Status PTKP')
    ptkp_amount = fields.Float(string='PTKP (Rp)')
    pkp_annual = fields.Float(string='PKP Setahun')
    pph21_terutang = fields.Float(string='PPh 21 Terutang Setahun')
    pph21_sudah_dipotong = fields.Float(string='PPh 21 Sudah Dipotong (12 bln)')
    pph21_bonus_thr = fields.Float(string='PPh 21 Bonus/THR')
    sisa_kurang_bayar = fields.Float(string='Sisa Kurang Bayar / (Lebih Bayar)')
    pph21_bulan_desember = fields.Float(string='PPh 21 Bulan Desember')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi'),
        ('submitted', 'Terkirim'),
    ], string='Status', default='draft', tracking=True)

    # ── XML Fields (SPT Masa PPh Unifikasi) ─────────────────────────────────
    period_month = fields.Selection([
        ('01', 'Januari'), ('02', 'Februari'), ('03', 'Maret'),
        ('04', 'April'), ('05', 'Mei'), ('06', 'Juni'),
        ('07', 'Juli'), ('08', 'Agustus'), ('09', 'September'),
        ('10', 'Oktober'), ('11', 'November'), ('12', 'Desember'),
    ], string='Masa Pajak', default='12')
    xml_content = fields.Text(string='XML Content')

    @api.depends('employee_id', 'year')
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or ''
            rec.display_name = f'SPT {rec.year} — {emp}'

    @api.model
    def create(self, vals_list):
        self._enforce_trial()
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.spt.tahunan.sequence'
                ) or '/'
        return super().create(vals_list)

    def action_compute(self):
        """Aggregate PPh 21 data dari semua slip gaji tahun ini."""
        for rec in self:
            pph21_records = self.env['hr.pph21'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('period_year', '=', rec.year),
            ], order='period_month')

            if not pph21_records:
                raise UserError(
                    f'Tidak ada data PPh 21 untuk {rec.employee_id.name} tahun {rec.year}.\n'
                    'Hitung gaji terlebih dahulu.'
                )

            # Aggregate income (12 months, exclude THR/bonus yang sudah terpisah)
            rec.total_gaji_pokok = sum(pph21_records.mapped('gaji_pokok')) * 12
            rec.total_tunj_tetap = sum(pph21_records.mapped('tunjangan_tetap')) * 12
            rec.total_tunj_lain = sum(pph21_records.mapped('tunjangan_lain')) * 12
            rec.total_bonus_thr = sum(pph21_records.mapped('bonus_thr'))
            rec.total_bruto_12_bulan = rec.total_gaji_pokok + rec.total_tunj_tetap + rec.total_tunj_lain
            rec.total_bruto = rec.total_bruto_12_bulan + rec.total_bonus_thr

            # BPJS
            rec.total_bpjs_tk = sum(pph21_records.mapped('bpjs_tk_jht_emp')) * 12
            rec.total_bpjs_kes = 0.0  # BPJS Kes is separate from PPh 21 deduction

            # Pengurang
            biaya_jabatan = sum(pph21_records.mapped('biaya_jabatan')) * 12
            iuran_pensiun = sum(pph21_records.mapped('iuran_pensiun_emp')) * 12
            rec.total_pengurang = biaya_jabatan + iuran_pensiun + rec.total_bpjs_tk

            # PTKP & PKP
            pph_first = pph21_records[0]
            rec.ptkp_status = pph_first.ptkp_status
            rec.ptkp_amount = pph_first.ptkp_amount
            rec.pkp_annual = pph_first.pkp_tahunan

            # PPh 21 terutang
            rec.pph21_terutang = pph_first.pph21_tahunan

            # PPh 21 sudah dipotong (Jan-Nov reguler + Desember + bonus/THR)
            rec.pph21_sudah_dipotong = sum(pph21_records.mapped('pph21_final'))

            # PPh 21 bonus/THR
            rec.pph21_bonus_thr = sum(pph21_records.mapped('pph21_bonus_thr'))

            # PPh 21 Desember
            des_record = pph21_records.filtered(lambda r: r.period_month == 12)
            rec.pph21_bulan_desember = des_record.pph21_final if des_record else 0.0

            # Sisa
            rec.sisa_kurang_bayar = rec.pph21_terutang - rec.pph21_sudah_dipotong

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Hanya SPT draft yang bisa dikonfirmasi.')
            if rec.pph21_terutang <= 0:
                raise UserError('Hitung SPT terlebih dahulu.')
            rec.state = 'confirmed'

    def action_generate_xml(self):
        """Generate XML SPT Masa PPh Unifikasi."""
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError('SPT harus dikonfirmasi terlebih dahulu.')

            xml_content = self._build_spt_xml(rec)
            rec.xml_content = xml_content

    def _build_spt_xml(self, rec):
        """Build XML SPT Masa PPh Unifikasi."""
        root = ET.Element('Root')
        root.set('xmlns', 'http://www.pajak.go.id/coretax')

        # Induk SPT
        induk = ET.SubElement(root, 'IndukSPT')

        def add(parent, tag, value):
            el = ET.SubElement(parent, tag)
            el.text = str(value) if value is not None else ''

        npwp = self._format_npwp(rec.employee_id.company_id.npwp or '')

        add(induk, 'NPWP', npwp)
        add(induk, 'NAMA_WP', rec.employee_id.company_id.name or '')
        add(induk, 'MASA_PAJAK', rec.period_month or '12')
        add(induk, 'TAHUN_PAJAK', str(rec.year))
        add(induk, 'JENIS_PAJAK', 'PPh Unifikasi')
        add(induk, 'KJS', '411128')
        add(induk, 'JUMLAH_PPH_DIPOTONG', rec.pph21_sudah_dipotong)
        add(induk, 'JUMLAH_PPH_DIBAYAR', rec.pph21_sudah_dipotong)
        add(induk, 'JUMLAH_PPH_DIPERBETULKAN', 0)
        add(induk, 'STATUS_SPT', 'Normal')
        add(induk, 'TANGGAL_SPT', fields.Date.today().isoformat())

        # Daftar I (Bukti Potong)
        daftar1 = ET.SubElement(root, 'DaftarI')
        add(daftar1, 'JUMLAH_BUPOT', 1)
        add(daftar1, 'JUMLAH_PPH', rec.pph21_sudah_dipotong)

        # Daftar II (PPh Disetor Sendiri)
        daftar2 = ET.SubElement(root, 'DaftarII')
        add(daftar2, 'JUMLAH_PPH_DIBAYAR', 0)

        # Lampiran I (Dokumen yang dipersamakan dengan Bupot)
        lampiran1 = ET.SubElement(root, 'LampiranI')
        add(lampiran1, 'JUMLAH_DOK', 0)

        xml_str = ET.tostring(root, encoding='unicode', xml_declaration=False)
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ', encoding=None)

    def _format_npwp(self, npwp):
        """Format NPWP ke 16 digit tanpa titik."""
        if not npwp:
            return ''
        cleaned = npwp.replace('.', '').replace('-', '').replace(' ', '')
        return cleaned.zfill(16)[:16]

    def action_download_xml(self):
        """Download XML SPT Masa."""
        self.ensure_one()
        if not self.xml_content:
            if self.state != 'confirmed':
                raise UserError('SPT harus dikonfirmasi terlebih dahulu.')
            self.action_generate_xml()

        attachment = self.env['ir.attachment'].create({
            'name': f'SPT_Masa_{self.name}.xml',
            'type': 'binary',
            'datas': base64.b64encode(self.xml_content.encode('utf-8')),
            'res_model': 'hr.spt.tahunan',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_export_ebupot(self):
        """Export ke e-Bupot."""
        self.ensure_one()
        ebupot = self.env['hr.ebupot'].create({
            'employee_id': self.employee_id.id,
            'year': self.year,
            'form_type': '1721A1',
        })
        ebupot.action_compute_from_payslip()
        ebupot.action_generate_xml()
        return {
            'type': 'ir.actions.act_window',
            'name': 'e-Bupot',
            'res_model': 'hr.ebupot',
            'res_id': ebupot.id,
            'view_mode': 'form',
            'target': 'new',
        }
