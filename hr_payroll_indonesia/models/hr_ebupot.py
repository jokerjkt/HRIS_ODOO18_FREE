# -*- coding: utf-8 -*-
"""
e-Bupot — Electronic Withholding Receipt (Bukti Potong Elektronik)
=================================================================
Generates XML for DJP e-Bupot Unifikasi from PPh 21 data.
Formulir 1721-A1 (karyawan tetap) / 1721-A2 (karyawan tidak tetap/ahli).
Sesuai spesifikasi Coretax DJP: https://coretaxdjp.pajak.go.id
"""
import base64
import xml.etree.ElementTree as ET
from xml.dom import minidom

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

    # ── XML Fields (sesuai spesifikasi Coretax DJP) ──────────────────────────
    nitku_pemotong = fields.Char(string='NITKU Pemotong')
    nitku_penerima = fields.Char(string='NITKU Penerima')
    sifat_pph = fields.Selection([
        ('Tanpa Fasilitas', 'Tanpa Fasilitas'),
        ('PPh Ditanggung Pemerintah', 'PPh Ditanggung Pemerintah'),
        ('Surat Keterangan Bebas', 'Surat Keterangan Bebas'),
        ('Fasilitas Lainnya', 'Fasilitas Lainnya'),
    ], string='Sifat PPh', default='Tanpa Fasilitas')
    status_bupot = fields.Selection([
        ('Normal', 'Normal'),
        ('Pembetulan', 'Pembetulan'),
        ('Pembatalan', 'Pembatalan'),
    ], string='Status Bupot', default='Normal')
    kode_dok_referensi = fields.Selection([
        ('01', 'Faktur Pajak'),
        ('02', 'Invoice'),
        ('03', 'Surat Perjanjian'),
        ('04', 'Bukti Pembayaran'),
        ('05', 'Akta Perikatan'),
        ('06', 'Surat Pernyataan'),
    ], string='Kode Dok. Referensi', default='01')
    nomor_dok_referensi = fields.Char(string='Nomor Dokumen Referensi')
    tanggal_dok_referensi = fields.Date(string='Tanggal Dokumen Referensi')
    tanggal_pemotongan = fields.Date(string='Tanggal Pemotongan',
                                      default=fields.Date.context_today)
    nama_penandatangan = fields.Char(string='Nama Penandatangan')
    tanggal_ttd = fields.Date(string='Tanggal Tanda Tangan',
                               default=fields.Date.context_today)

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
                'nama_penandatangan': rec.employee_id.company_id.name or '',
            })

    def action_generate_xml(self):
        """Generate XML untuk e-Bupot DJP sesuai spesifikasi Coretax."""
        for rec in self:
            if rec.pph21_total <= 0:
                raise UserError('PPh 21 total harus lebih dari 0.')
            if not rec.tanggal_pemotongan:
                raise UserError('Tanggal pemotongan harus diisi.')

            xml_content = self._build_bppu_xml(rec)
            rec.write({
                'xml_content': xml_content,
                'state': 'exported',
            })

    def _build_bppu_xml(self, rec):
        """Build XML BPPU sesuai format Coretax DJP."""
        root = ET.Element('Root')
        root.set('xmlns', 'http://www.pajak.go.id/coretax')

        bppu = ET.SubElement(root, 'BPPU')

        def add(parent, tag, value):
            el = ET.SubElement(parent, tag)
            el.text = str(value) if value is not None else ''

        npwp_pemotong = self._format_npwp(rec.employee_id.company_id.npwp or '')
        npwp_penerima = self._format_npwp(rec.npwp or '')

        add(bppu, 'NPWP_PEMOTONG', npwp_pemotong)
        add(bppu, 'NAMA_PEMOTONG', rec.employee_id.company_id.name or '')
        add(bppu, 'NITKU_PEMOTONG', rec.nitku_pemotong or '')
        add(bppu, 'MPWP', npwp_penerima)
        add(bppu, 'NAMA_PENERIMA', rec.employee_id.name or '')
        add(bppu, 'NITKU_PENERIMA', rec.nitku_penerima or '')
        add(bppu, 'MASA_PAJAK', f'{rec.tanggal_pemotongan.month:02d}')
        add(bppu, 'TAHUN_PAJAK', str(rec.year))
        add(bppu, 'KODE_PAJAK', '411128')
        add(bppu, 'SIFAT_PPH', rec.sifat_pph or 'Tanpa Fasilitas')
        add(bppu, 'STATUS_BUPOT', rec.status_bupot or 'Normal')
        add(bppu, 'DPP', rec.pkp)
        add(bppu, 'TARIF', 5)
        add(bppu, 'PPH_DIPOTONG', rec.pph21_total)
        add(bppu, 'KODE_DOK_REFERENSI', rec.kode_dok_referensi or '01')
        add(bppu, 'NOMOR_DOK_REFERENSI', rec.nomor_dok_referensi or '')
        add(bppu, 'TANGGAL_DOK_REFERENSI',
            rec.tanggal_dok_referensi.isoformat() if rec.tanggal_dok_referensi else '')
        add(bppu, 'TANGGAL_PEMOTONGAN', rec.tanggal_pemotongan.isoformat())
        add(bppu, 'NAMA_PENANDATANGAN', rec.nama_penandatangan or '')
        add(bppu, 'TANGGAL_TTD', rec.tanggal_ttd.isoformat() if rec.tanggal_ttd else '')

        xml_str = ET.tostring(root, encoding='unicode', xml_declaration=False)
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ', encoding=None)

    def _format_npwp(self, npwp):
        """Format NPWP ke 16 digit tanpa titik."""
        if not npwp:
            return ''
        cleaned = npwp.replace('.', '').replace('-', '').replace(' ', '')
        return cleaned.zfill(16)[:16]

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

    def action_download_xml(self):
        """Download XML sebagai file."""
        self.ensure_one()
        if not self.xml_content:
            self.action_generate_xml()

        attachment = self.env['ir.attachment'].create({
            'name': f'eBupot_{self.name}.xml',
            'type': 'binary',
            'datas': base64.b64encode(self.xml_content.encode('utf-8')),
            'res_model': 'hr.ebupot',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_template(self):
        """Download template XML kosong untuk referensi."""
        template = '''<?xml version="1.0" encoding="UTF-8"?>
<!--
  Template e-Bupot Unifikasi (BPPU)
  Sesuai PER-24/PJ/2021 dan PER-11/PJ/2025

  Isi field sesuai data PPh 21 karyawan.
  Upload ke Coretax DJP Online: https://coretaxdjp.pajak.go.id
-->
<Root xmlns="http://www.pajak.go.id/coretax">
  <BPPU>
    <NPWP_PEMOTONG>1234567890123456</NPWP_PEMOTONG>
    <NAMA_PEMOTONG>Nama Perusahaan</NAMA_PEMOTONG>
    <NITKU_PEMOTONG></NITKU_PEMOTONG>
    <MPWP>1234567890123456</MPWP>
    <NAMA_PENERIMA>Nama Karyawan</NAMA_PENERIMA>
    <NITKU_PENERIMA></NITKU_PENERIMA>
    <MASA_PAJAK>12</MASA_PAJAK>
    <TAHUN_PAJAK>2026</TAHUN_PAJAK>
    <KODE_PAJAK>411128</KODE_PAJAK>
    <SIFAT_PPH>Tanpa Fasilitas</SIFAT_PPH>
    <STATUS_BUPOT>Normal</STATUS_BUPOT>
    <DPP>50000000</DPP>
    <TARIF>5</TARIF>
    <PPH_DIPOTONG>2500000</PPH_DIPOTONG>
    <KODE_DOK_REFERENSI>01</KODE_DOK_REFERENSI>
    <NOMOR_DOK_REFERENSI>INV-001</NOMOR_DOK_REFERENSI>
    <TANGGAL_DOK_REFERENSI>2026-12-31</TANGGAL_DOK_REFERENSI>
    <TANGGAL_PEMOTONGAN>2026-12-31</TANGGAL_PEMOTONGAN>
    <NAMA_PENANDATANGAN>Direktur</NAMA_PENANDATANGAN>
    <TANGGAL_TTD>2026-12-31</TANGGAL_TTD>
  </BPPU>
</Root>'''

        attachment = self.env['ir.attachment'].create({
            'name': 'Template_eBupot_BPPU.xml',
            'type': 'binary',
            'datas': base64.b64encode(template.encode('utf-8')),
            'res_model': 'hr.ebupot',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
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

    def action_export_batch_xml(self):
        """Export multiple e-Bupot ke satu file XML (batch)."""
        ebupots = self.search([('state', 'in', ('draft', 'exported'))])
        if not ebupots:
            raise UserError('Tidak ada e-Bupot untuk di-export.')

        root = ET.Element('Root')
        root.set('xmlns', 'http://www.pajak.go.id/coretax')

        for rec in ebupots:
            if rec.pph21_total <= 0:
                continue
            if not rec.tanggal_pemotongan:
                continue

            bppu = ET.SubElement(root, 'BPPU')

            def add(parent, tag, value):
                el = ET.SubElement(parent, tag)
                el.text = str(value) if value is not None else ''

            npwp_pemotong = self._format_npwp(rec.employee_id.company_id.npwp or '')
            npwp_penerima = self._format_npwp(rec.npwp or '')

            add(bppu, 'NPWP_PEMOTONG', npwp_pemotong)
            add(bppu, 'NAMA_PEMOTONG', rec.employee_id.company_id.name or '')
            add(bppu, 'NITKU_PEMOTONG', rec.nitku_pemotong or '')
            add(bppu, 'MPWP', npwp_penerima)
            add(bppu, 'NAMA_PENERIMA', rec.employee_id.name or '')
            add(bppu, 'NITKU_PENERIMA', rec.nitku_penerima or '')
            add(bppu, 'MASA_PAJAK', f'{rec.tanggal_pemotongan.month:02d}')
            add(bppu, 'TAHUN_PAJAK', str(rec.year))
            add(bppu, 'KODE_PAJAK', '411128')
            add(bppu, 'SIFAT_PPH', rec.sifat_pph or 'Tanpa Fasilitas')
            add(bppu, 'STATUS_BUPOT', rec.status_bupot or 'Normal')
            add(bppu, 'DPP', rec.pkp)
            add(bppu, 'TARIF', 5)
            add(bppu, 'PPH_DIPOTONG', rec.pph21_total)
            add(bppu, 'KODE_DOK_REFERENSI', rec.kode_dok_referensi or '01')
            add(bppu, 'NOMOR_DOK_REFERENSI', rec.nomor_dok_referensi or '')
            add(bppu, 'TANGGAL_DOK_REFERENSI',
                rec.tanggal_dok_referensi.isoformat() if rec.tanggal_dok_referensi else '')
            add(bppu, 'TANGGAL_PEMOTONGAN', rec.tanggal_pemotongan.isoformat())
            add(bppu, 'NAMA_PENANDATANGAN', rec.nama_penandatangan or '')
            add(bppu, 'TANGGAL_TTD', rec.tanggal_ttd.isoformat() if rec.tanggal_ttd else '')

        xml_str = ET.tostring(root, encoding='unicode', xml_declaration=False)
        dom = minidom.parseString(xml_str)
        xml_content = dom.toprettyxml(indent='  ', encoding=None)

        attachment = self.env['ir.attachment'].create({
            'name': f'eBupot_BPPU_Batch_{ebupots[0].year}_{fields.Date.today().strftime("%Y%m%d")}.xml',
            'type': 'binary',
            'datas': base64.b64encode(xml_content.encode('utf-8')),
            'res_model': 'hr.ebupot',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
