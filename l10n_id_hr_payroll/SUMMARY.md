# Indonesian HR Payroll System — Odoo 18

**Modul HR Payroll Indonesia untuk Odoo 18 Community**
Integrated HR payroll solution for Indonesian companies.

---

## Overview

Complete HR payroll system built as a standalone module for Odoo 18 Community (no Enterprise dependencies). Fully integrated with Odoo 18's standard HR app — appears as native sub-menus under the Employees app.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Odoo 18 Community Core                      │
│  hr │ hr_contract │ hr_work_entry │ hr_attendance │ ... │
└──────────────────────┬──────────────────────────────────┘
                       │ _inherit (extends)
                       ▼
┌─────────────────────────────────────────────────────────┐
│         l10n_id_hr_payroll — Indonesian HR               │
│                                                         │
│  Employee Extension    │  Department Extension           │
│  (NIK, NPWP, PTKP,    │  (Code for payslip             │
│   BPJS, Bank info)     │   numbering)                   │
│                        │                                │
│  Contract Extension    │  Payslip (Standalone)           │
│  (Allowances)          │  (GJ.MM.YYYY/DDD/NNN)          │
│                        │                                │
│  PPh 21 Engine  │  BPJS Engine  │  Overtime Engine      │
│  (Progresif 5-  │  (TK + Kes)   │  (Permenaker 5/2023) │
│   35%)          │               │                       │
│                 │               │                       │
│  THR Engine     │  Dashboard    │  Bank Payment List     │
│  (Proporsional) │  (Admin+User) │  (PDF Report)          │
│                 │               │                       │
│  Trial Mixin    │  Demo Data    │  Reports               │
│  (5-day,        │  (5 employees)│  (Slip Gaji, Bukti     │
│   bypass-proof) │               │   Potong, Rekap BPJS)  │
│                 │               │                       │
│  Shift Scheduling System                              │
│  (3-shift weekly / 4-shift daily rotation)            │
└─────────────────────────────────────────────────────────┘
```

---

## Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **PPh 21** | Auto progressive tax 5%-35% (UU HPP No. 7/2021) |
| 2 | **BPJS Ketenagakerjaan** | JKK, JKM, JHT, JP with risk-based rates |
| 3 | **BPJS Kesehatan** | 1% employee, 4% employer (cap Rp 12M) |
| 4 | **Payslip** | Transaction number GJ.MM.YYYY/DDD/NNN, workflow draft→computed→done |
| 5 | **Bulk Payslip** | Wizard to generate payslips for all employees at once |
| 6 | **Overtime** | Permenaker 5/2023 multipliers, approval workflow |
| 7 | **THR** | Proportional calculation, bulk generation wizard |
| 8 | **Dashboard Admin** | Full stats, quick actions for HR managers |
| 9 | **Dashboard HR User** | Simplified view for regular HR users |
| 10 | **Bank Payment** | List view + PDF report for bank transfer |
| 11 | **Reports** | Slip Gaji PDF, Bukti Potong 1721, Rekap BPJS |
| 12 | **Trial Mode** | 5-day bypass-proof trial, read-only after expiry |
| 13 | **Demo Data** | Sample employees, contracts ready to test |
| 14 | **Shift Scheduling** | 3-shift weekly / 4-shift daily rotation with Gantt view |
| 15 | **Bulk Shift Assign** | Wizard to assign shifts to multiple employees |
| 16 | **Holiday Integration** | Auto-detect public holidays from hr.holiday |
| 17 | **Role/Group System** | 4-level security (Pegawai → Admin → Supervisor → Full Admin) |
| 18 | **Attendance Device Integration** | Multi-brand support: ZKTeco, Solution, Fingerspot, ATT2000 |
| 19 | **CSV/Excel Import** | Universal import from any attendance machine |
| 20 | **ZKTeco Direct** | TCP/UDP connection via PyZK library |
| 21 | **ADMS Cloud Push** | Flask server for ZKTeco push data |
| 22 | **Device Registry** | Manage multiple attendance machines |
| 23 | **Attendance Log Viewer** | View and match raw attendance logs |
| 24 | **Data Isolation** | Record rules for payslip/THR/attendance |
| 25 | **API Key Auth** | Flask ADMS secured with API key |
| 26 | **Unit Tests** | 42 tests covering all modules |

---

## File Structure (80 files)

```
l10n_id_hr_payroll/
├── __manifest__.py
├── __init__.py
├── hooks.py                          # Post-init: trial date + dept codes
├── models/
│   ├── __init__.py
│   ├── trial_mixin.py                # Bypass-proof trial logic (3-layer)
│   ├── hr_department.py              # Extension: code field
│   ├── hr_employee.py                # Extension: NIK, NPWP, PTKP, BPJS, Bank
│   ├── hr_pph21.py                   # PPh 21 engine (progressive 5-35%)
│   ├── hr_bpjs.py                    # BPJS engine (TK + Kesehatan)
│   ├── hr_bpjs_rate.py               # BPJS rate config by risk class
│   ├── hr_contract.py                # Extension: allowances
│   ├── hr_overtime.py                # Overtime with approval workflow
│   ├── hr_payslip.py                 # Payslip (standalone, GJ.MM.YYYY/DDD/NNN)
│   ├── hr_thr.py                     # THR calculator (proportional)
│   ├── hr_payroll_dashboard.py       # Admin dashboard (TransientModel)
│   ├── hr_user_dashboard.py          # HR User dashboard (TransientModel)
│   ├── hr_my_dashboard.py            # Personal dashboard (TransientModel)
│   ├── hr_shift_type.py              # Shift type definitions
│   ├── hr_shift_rotation.py          # Rotation patterns
│   ├── hr_shift_assign.py            # Assign rotation to employee
│   ├── hr_shift_daily.py             # Generated daily schedule
│   ├── hr_attendance_device.py       # Device registry (ZKTeco, Solution, etc.)
│   ├── hr_attendance_device_log.py   # Raw attendance logs from devices
│   ├── hr_attendance_extend.py       # Extend hr.attendance with device fields
│   ├── hr_attendance_connector.py    # Abstract connector base class
│   ├── hr_attendance_connector_csv.py # CSV/Excel universal connector
│   └── hr_attendance_connector_zkteco.py # ZKTeco direct connector (PyZK)
├── wizard/
│   ├── __init__.py
│   ├── hr_thr_wizard.py              # Bulk THR generation
│   ├── hr_thr_wizard_views.xml
│   ├── hr_payslip_generate_wizard.py # Bulk payslip generation
│   ├── hr_payslip_generate_views.xml
│   ├── hr_shift_bulk_assign.py       # Bulk shift assignment
│   ├── hr_shift_bulk_assign_views.xml
│   ├── hr_attendance_import.py       # Attendance import wizard
│   └── hr_attendance_import_views.xml
├── data/
│   ├── hr_bpjs_rate_data.xml         # 5 BPJS risk groups
│   ├── hr_leave_type_data.xml        # 8 Indonesian leave types
│   ├── hr_shift_type_data.xml        # 4 default shift types + rotation templates
│   └── hr_demo_data.xml              # Demo employees & contracts
├── security/
│   ├── ir.model.access.csv           # ACL for all models
│   ├── hr_overtime_security.xml      # Overtime groups + record rules
│   ├── hr_role_security.xml          # 4-level role groups
│   ├── hr_attendance_security.xml    # Record rules for data isolation
│   └── hr_payroll_security.xml       # Dashboard ACL
├── views/
│   ├── hr_employee_views.xml         # Indonesia HR tab on employee form
│   ├── hr_department_views.xml       # Code field on department
│   ├── hr_contract_views.xml         # Allowance fields on contract
│   ├── hr_payslip_views.xml          # Payslip form/list/search
│   ├── hr_payslip_payment_views.xml  # Bank payment list
│   ├── hr_overtime_views.xml         # Overtime form/list/kanban
│   ├── hr_thr_views.xml              # THR form/list
│   ├── hr_bpjs_rate_views.xml        # BPJS rate list/form
│   ├── hr_shift_type_views.xml       # Shift type list/form
│   ├── hr_shift_rotation_views.xml   # Rotation pattern form/list
│   ├── hr_shift_assign_views.xml     # Assign shift form/list
│   ├── hr_shift_daily_views.xml      # Daily schedule Gantt/calendar/list
│   ├── hr_attendance_device_views.xml    # Device list/form
│   ├── hr_attendance_device_log_views.xml # Log list/form
│   ├── hr_attendance_views.xml           # Extended attendance views
│   ├── hr_my_dashboard_views.xml     # Personal dashboard
│   ├── hr_user_dashboard_views.xml   # HR User dashboard
│   ├── dashboard_views.xml           # Admin dashboard
│   └── menu_views.xml                # Integrated under HR app
├── report/
│   ├── hr_payslip_report.xml         # Slip Gaji PDF
│   ├── hr_bukti_potong_report.xml    # Bukti Potong 1721-A1/A2
│   ├── hr_bpjs_report.xml            # Rekap Iuran BPJS
│   └── hr_bank_payment_report.xml    # Daftar Pembayaran Bank
├── static/
│   └── description/
│       ├── icon.png
│       └── index.html                # Module description page
├── SUMMARY.md
├── MODULE_DESIGN.md
├── tests/
│   ├── __init__.py
│   ├── test_pph21.py                   # PPh 21 progressive tax tests
│   ├── test_bpjs.py                    # BPJS computation tests
│   ├── test_thr.py                     # THR calculation tests
│   ├── test_payslip.py                 # Payslip workflow tests
│   ├── test_csv_parser.py              # CSV/Excel parser tests
│   ├── test_employee.py                # Employee fields tests
│   └── test_attendance.py              # Attendance device tests
├── flask_adms/
│   ├── __init__.py
│   ├── app.py                          # Flask ADMS server (ZKTeco push)
│   └── config.py                       # Configuration
└── run_adms.py                         # ADMS server entry point
```

---

## Installation

1. Copy `l10n_id_hr_payroll` to Odoo 18 addons directory
2. Update Apps List (Settings → Developer Mode → Update Apps List)
3. Install **Indonesian HR Payroll (PPh 21 & BPJS)**
4. Dependencies: `hr`, `hr_contract`, `hr_work_entry`, `hr_attendance`, `hr_holidays`, `hr_expense`, `mail`

---

## Usage Guide

### Setup Karyawan
1. **Employees** → select employee → **Indonesia HR** tab
2. Fill NIK, NPWP, PTKP status, BPJS info, bank details

### Proses Payroll
1. **Employees → Payroll → Daftar Slip Gaji** → New
2. Select employee and period
3. Click **Hitung Gaji** → PPh 21 & BPJS auto-calculated
4. Review tabs: PPh 21 | BPJS | Lembur | THR
5. **Konfirmasi** → Done

### Bulk Payslip Generation
1. **Employees → Payroll → Buat Slip Gaji Massal**
2. Select period, filter departments/employees
3. Preview count and estimated total
4. Click **Buat Slip Gaji** → Auto-compute all

### Lembur
1. **Employees → Lembur → Pengajuan Lembur Saya**
2. New → fill date, hours, activity description
3. **Submit ke Atasan** → Manager reviews
4. Approved overtime → auto-linked to payslip

### THR
1. **Employees → THR → Generate THR Massal**
2. Fill year, holiday, payment date
3. Preview eligible employees
4. **Generate THR** → Confirm → Mark paid

### Shift Scheduling
1. **Configuration → Tipe Shift** — Define shift types (Pagi/Siang/Malam/Libur)
2. **Configuration → Pola Rotasi Shift** — Create rotation patterns
3. **Shift Scheduling → Assign Shift** — Assign rotation to employee
4. **Shift Scheduling → Generate Bulk Assign** — Assign to multiple employees
5. **Shift Scheduling → Jadwal Harian** — View Gantt/Calendar schedule

### Attendance Device Integration
1. **Mesin Absensi → Daftar Mesin** — Add attendance machine
2. Select brand (ZKTeco/Solution/Fingerspot/ATT2000) and connection type
3. For CSV Import: Set connection type to "File Import Only"
4. **Mesin Absensi → Import Absensi** — Import from file or pull from device
5. Upload CSV/Excel → Parse → Preview → Import
6. **Mesin Absensi → Log dari Mesin** — View raw logs and match employees

### Cetak Laporan
- **Slip Gaji**: from Payslip → Print → Slip Gaji Indonesia
- **Bukti Potong**: from Payslip → Print → Bukti Potong PPh 21
- **Rekap BPJS**: from menu → Rekap Iuran BPJS

---

## Menu Integration

Integrated under Odoo 18 HR app (Employees):

```
HR App (Employees)
├── Dashboard Saya (top navbar)
├── Dashboard HR (top navbar)
├── Dashboard Admin (HR Managers)
├── Payroll
│   ├── Daftar Slip Gaji
│   ├── Daftar Pembayaran Gaji
│   └── Buat Slip Gaji Massal
├── Lembur
│   ├── Pengajuan Lembur Saya
│   ├── Perlu Persetujuan
│   └── Semua Lembur
├── THR
│   ├── Daftar THR
│   └── Generate THR Massal
├── Shift Scheduling
│   ├── Jadwal Harian (Gantt view)
│   ├── Assign Shift
│   └── Generate Bulk Assign
├── Mesin Absensi
│   ├── Daftar Mesin
│   ├── Log dari Mesin
│   └── Import Absensi
├── Reporting → Rekap Iuran BPJS
└── Configuration
    ├── Tipe Shift
    ├── Pola Rotasi Shift
    └── Tarif BPJS
```

---

## Trial Mode

- **Duration**: 5 days from installation
- **Bypass-proof**: 3-layer verification (config + checksum + DB timestamps)
- **After expiry**: Read-only mode (can view data, cannot create/edit/compute)
- **Bilingual**: Indonesian + English messages
- **Contact**: susilo.cdv@gmail.com | linkedin.com/in/susilo-raden-68a19049

---

## Regulatory References

| Regulation | Subject |
|------------|---------|
| UU HPP No. 7/2021 | Progressive PPh 21 rates |
| PMK No. 168/PMK.010/2023 | PPh 21 withholding procedures |
| PMK No. 101/PMK.010/2016 | PTKP table |
| PP No. 44/2015 | BPJS TK — JKK & JKM |
| PP No. 46/2015 | BPJS TK — JHT |
| PP No. 45/2015 | BPJS TK — JP |
| Perpres No. 75/2019 | BPJS Kesehatan |
| PerBPJS No. 6/2023 | Updated BPJS Kesehatan rates |
| PP No. 36/2021 | THR (Holiday Allowance) |
| Permenaker No. 5/2023 | Overtime pay rates |

---

## Contact

- **Email**: susilo.cdv@gmail.com
- **LinkedIn**: [Susilo Raden](https://www.linkedin.com/in/susilo-raden-68a19049)

---

*Last updated: 2026-07-20 (Phase 3b: Bug Fixes, Security, Tests)*
