/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

class HelpGuide extends Component {
    setup() {
        this.state = useState({
            activeSection: 'setup',
        });

        this.sections = [
            { id: 'setup', title: 'Setup Awal', icon: 'fa-cog' },
            { id: 'karyawan', title: 'Setup Karyawan', icon: 'fa-users' },
            { id: 'payroll', title: 'Proses Payroll', icon: 'fa-money' },
            { id: 'lembur', title: 'Lembur', icon: 'fa-clock-o' },
            { id: 'thr', title: 'THR', icon: 'fa-gift' },
            { id: 'shift', title: 'Shift Scheduling', icon: 'fa-calendar' },
            { id: 'absensi', title: 'Absensi Device', icon: 'fa-qrcode' },
            { id: 'mobile', title: 'Absensi Mobile', icon: 'fa-mobile' },
            { id: 'ebupot', title: 'e-Bupot & SPT', icon: 'fa-file-text' },
            { id: 'bpjs', title: 'BPJS', icon: 'fa-hospital-o' },
            { id: 'laporan', title: 'Laporan', icon: 'fa-print' },
            { id: 'role', title: 'Role & Hak Akses', icon: 'fa-shield' },
        ];

        this.guides = {
            setup: {
                title: 'Setup Awal Sistem',
                steps: [
                    'Login sebagai Admin (admin/admin)',
                    'Masuk ke menu Employees',
                    'Pastikan data perusahaan sudah lengkap (NPWP, alamat)',
                    'Setup Department (kode untuk penomoran slip gaji)',
                    'Setup Tarif BPJS di Configuration → Tarif BPJS',
                ],
            },
            karyawan: {
                title: 'Setup Karyawan',
                steps: [
                    'Buka Employees → pilih karyawan',
                    'Klik tab "Indonesia HR"',
                    'Isi NIK (16 digit angka)',
                    'Isi NPWP (15 atau 16 digit angka)',
                    'Pilih Status PTKP (TK/0, K/1, dll)',
                    'Isi No. BPJS TK dan BPJS Kes',
                    'Isi informasi bank (nama bank, no. rekening)',
                ],
            },
            payroll: {
                title: 'Proses Payroll (Slip Gaji)',
                steps: [
                    'Buka Employees → Payroll → Daftar Slip Gaji',
                    'Klik "New" untuk buat slip gaji baru',
                    'Pilih karyawan dan periode gaji',
                    'Klik "Hitung Gaji" → PPh 21 & BPJS otomatis terhitung',
                    'Review tab: PPh 21 | BPJS | Lembur | THR',
                    'Klik "Konfirmasi" untuk finalisasi',
                    'Untuk massal: Payroll → Buat Slip Gaji Massal',
                ],
            },
            lembur: {
                title: 'Pengajuan Lembur',
                steps: [
                    'Buka Employees → Lembur → Pengajuan Lembur Saya',
                    'Klik "New" → isi tanggal, jam, aktivitas',
                    'Klik "Submit ke Atasan"',
                    'Atasan review di menu "Perlu Persetujuan"',
                    'Setelah disetujui, lembur otomatis terhubung ke slip gaji',
                ],
            },
            thr: {
                title: 'THR (Tunjangan Hari Raya)',
                steps: [
                    'Buka Employees → THR → Daftar THR',
                    'Klik "Generate THR Massal"',
                    'Isi tahun pajak, tanggal libur, tanggal bayar',
                    'Preview karyawan yang berhak',
                    'Klik "Generate THR" → Konfirmasi → Tandai sudah dibayar',
                ],
            },
            shift: {
                title: 'Shift Scheduling',
                steps: [
                    'Configuration → Tipe Shift (Pagi/Siang/Malam/Libur)',
                    'Configuration → Pola Rotasi Shift (buat pola)',
                    'Shift Scheduling → Assign Shift (ke karyawan)',
                    'Shift Scheduling → Generate Bulk Assign (massal)',
                    'Shift Scheduling → Jadwal Harian (lihat Gantt/Calendar)',
                ],
            },
            absensi: {
                title: 'Absensi Device (Mesin Finger)',
                steps: [
                    'Attendances → Mesin Absensi → Daftar Mesin',
                    'Tambah mesin baru (pilih brand: ZKTeco/Solution/etc)',
                    'Untuk CSV: set connection type "File Import Only"',
                    'Attendances → Import Absensi → upload file CSV/Excel',
                    'Preview → Import → Data otomatis masuk ke sistem',
                ],
            },
            mobile: {
                title: 'Absensi Mobile (PWA)',
                steps: [
                    'Buka Odoo di browser mobile (Chrome/Safari)',
                    'Login dengan akun karyawan',
                    'Buka menu "Absensi Mobile"',
                    'Izinkan akses Kamera dan GPS',
                    'Ambil selfie → Submit',
                    'Sistem otomatis deteksi Check-in / Check-out',
                ],
            },
            ebupot: {
                title: 'e-Bupot & SPT Tahunan',
                steps: [
                    'Employees → Reporting → e-Bupot',
                    'Klik "New" → pilih karyawan → tahun pajak',
                    'Klik "Ambil Data PPh 21"',
                    'Isi tanggal pemotongan, nama penandatangan',
                    'Klik "Generate XML" → Download XML',
                    'Upload XML ke Coretax DJP Online',
                    'Untuk SPT: Reporting → SPT Tahunan → Generate XML SPT',
                ],
            },
            bpjs: {
                title: 'BPJS Submission',
                steps: [
                    'Employees → Reporting → Rekap Iuran BPJS',
                    'Klik "New" → pilih jenis (TK/Kesehatan)',
                    'Isi bulan dan tahun',
                    'Klik "Generate Data Iuran"',
                    'Klik "Generate CSV" untuk download file',
                    'Upload CSV ke portal BPJS SPT Management',
                ],
            },
            laporan: {
                title: 'Cetak Laporan',
                steps: [
                    'Slip Gaji: Pilih slip → Print → Slip Gaji Indonesia',
                    'Bukti Potong: Pilih slip → Print → Bukti Potong PPh 21',
                    'Rekap BPJS: Reporting → Rekap Iuran BPJS → Print',
                    'Bank Payment: Payroll → Daftar Pembayaran → Print',
                ],
            },
            role: {
                title: 'Role & Hak Akses',
                items: [
                    { role: 'Pegawai (group_hr_user)', akses: 'Lihat data sendiri, submit lembur' },
                    { role: 'Admin HR (group_hr_admin)', akses: 'CRD payslip, THR, manage shift' },
                    { role: 'Supervisor (group_hr_supervisor)', akses: 'Approve lembur, view rekap BPJS' },
                    { role: 'Full Admin (group_hr_full_admin)', akses: 'Full akses + dashboard admin' },
                ],
            },
        };
    }

    selectSection(sectionId) {
        this.state.activeSection = sectionId;
    }

    get currentGuide() {
        return this.guides[this.state.activeSection];
    }
}

HelpGuide.template = "l10n_id_hr_payroll.HelpGuide";

registry.category("actions").add("l10n_id_hr_payroll.help_guide", HelpGuide);
