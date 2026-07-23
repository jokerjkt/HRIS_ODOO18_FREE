# MODULE_DESIGN.md — Desain Teknis Modul `l10n_id_hr_payroll`

**Modul HR Payroll Indonesia untuk Odoo 18 Community**
*Last updated: 2026-07-23*

---

## Overview Arsitektur

```
┌─────────────────────────────────────────────────────────┐
│                    Odoo 18 Community                     │
│  hr  │  hr_contract  │  hr_work_entry  │  hr_holidays   │
│  hr_attendance  │  hr_expense  │  mail                  │
└──────────────────────┬──────────────────────────────────┘
                       │ extends / inherit
                       ▼
┌─────────────────────────────────────────────────────────┐
│            l10n_id_hr_payroll (Module Kita)              │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ hr_employee  │  │  hr_pph21    │  │   hr_bpjs    │  │
│  │ (extension)  │  │  (engine)    │  │   (engine)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ hr_overtime  │  │  hr_payslip  │  │   hr_thr     │  │
│  │ (new model)  │  │  (standalone)│  │ (new model)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Shift Scheduling System                        │    │
│  │  hr.shift.type │ hr.shift.rotation              │    │
│  │  hr.shift.assign │ hr.shift.daily               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Attendance Device Integration                  │    │
│  │  hr.attendance.device │ hr.attendance.device.log│    │
│  │  Connectors: CSV │ ZKTeco │ Solution            │    │
│  │  Flask ADMS Server (port 8068)                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  e-Bupot & SPT Tahunan                         │    │
│  │  hr.ebupot │ hr.spt.tahunan │ hr.bpjs.submission│    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  PWA Mobile Attendance (Selfie + GPS)           │    │
│  │  OWL Component + Service Worker                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Trial Mixin (bypass-proof, 3-layer check)      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Reports: Slip Gaji | Bukti Potong | Rekap BPJS │    │
│  │          | Daftar Pembayaran Bank               │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Dependencies

```python
'depends': [
    'hr',
    'hr_contract',
    'hr_work_entry',
    'hr_attendance',
    'hr_holidays',
    'hr_expense',
    'mail',
],
```

---

## Model Design

### Extension Models (inherit from Odoo core)

| Model | Inherits | Fields Added |
|-------|----------|--------------|
| `hr.employee` | `hr.employee` | NIK, NPWP, PTKP status, BPJS TK/Kes info, bank account, join_date |
| `hr.department` | `hr.department` | code (for payslip numbering) |
| `hr.contract` | `hr.contract` | x_tunjangan_tetap, x_tunjangan_tidak_tetap (allowances) |
| `hr.attendance` | `hr.attendance` | device_id, device_log_id, punch_type, verify_mode, is_from_device, check_in/out photos, GPS fields |

### Standalone Models (custom _name)

| Model | Description | Inherits |
|-------|-------------|----------|
| `hr.payslip` | Payslip (GJ.MM.YYYY/DDD/NNN) | mail.thread, trial.mixin |
| `hr.pph21` | PPh 21 calculation detail | — |
| `hr.bpjs` | BPJS contribution detail | — |
| `hr.bpjs.rate` | BPJS rate config by risk class | — |
| `hr.bpjs.api.config` | BPJS API credentials | — |
| `hr.bpjs.submission` | BPJS submission records | mail.thread, trial.mixin |
| `hr.overtime` | Overtime with approval workflow | mail.thread, mail.activity.mixin, trial.mixin |
| `hr.thr` | THR (holiday allowance) | mail.thread, trial.mixin |
| `hr.ebupot` | e-Bupot PPh 21 withholding | mail.thread, trial.mixin |
| `hr.spt.tahunan` | SPT Tahunan PPh 21 | mail.thread, trial.mixin |
| `hr.shift.type` | Shift type definitions (Pagi/Siang/Malam/Libur) | — |
| `hr.shift.rotation` | Rotation pattern (3-shift weekly / 4-shift daily) | — |
| `hr.shift.rotation.line` | Detail of rotation cycle (day X → shift type) | — |
| `hr.shift.assign` | Assign rotation to employee for period | — |
| `hr.shift.daily` | Generated daily shift schedule | — |
| `hr.payroll.dashboard` | Admin dashboard (TransientModel) | — |
| `hr.user.dashboard` | HR User dashboard (TransientModel) | — |
| `hr.my.dashboard` | Personal dashboard (TransientModel) | — |
| `hr.attendance.device` | Device registry (ZKTeco, Solution, etc.) | mail.thread, mail.activity.mixin |
| `hr.attendance.device.log` | Raw attendance logs from devices | — |
| `hr.attendance.geo.fence` | Geo-fence zone definitions | — |

### Abstract Models (connectors)

| Model | Description |
|-------|-------------|
| `hr.attendance.connector` | Abstract base connector |
| `hr.attendance.connector.csv` | CSV/Excel universal connector |
| `hr.attendance.connector.zkteco` | ZKTeco direct connector (PyZK) |

### TransientModels (wizards)

| Model | Description |
|-------|-------------|
| `hr.thr.wizard` | Bulk THR generation |
| `hr.payslip.generate.wizard` | Bulk payslip generation |
| `hr.shift.bulk.assign` | Bulk shift assignment wizard |
| `hr.attendance.import.wizard` | Attendance import from file/device |
| `hr.attendance.import.wizard.line` | Preview line for import wizard |
| `hr.efiling.wizard` | e-Filing DJP online (e-Bupot, SPT) |
| `hr.bpjs.upload.wizard` | BPJS CSV submission upload |

---

## Menu Structure

```
HR App (Employees)
├── Dashboard Saya
├── Dashboard HR
├── Dashboard Admin
├── Daftar Slip Gaji Saya
├── ── Payroll ──
│   ├── Daftar Slip Gaji
│   ├── Daftar Pembayaran Gaji
│   └── Buat Slip Gaji Massal
├── ── Lembur ──
│   ├── Pengajuan Lembur Saya
│   ├── Perlu Persetujuan
│   └── Semua Lembur
├── ── THR ──
│   ├── Daftar THR
│   ├── Generate THR Massal
│   └── THR Saya
├── ── Shift Scheduling ──
│   ├── Jadwal Harian (Gantt/Calendar/List)
│   ├── Assign Shift
│   └── Generate Bulk Assign
├── ── Reporting ──
│   └── Rekap Iuran BPJS

Attendances App
├── ── Mesin Absensi ──
│   ├── Daftar Mesin
│   ├── Log dari Mesin
│   ├── Import Absensi
│   └── Geo-Fence Lokasi
├── Absensi Mobile (Selfie + GPS)

Configuration (under HR)
├── Tipe Shift
├── Pola Rotasi Shift
└── Tarif BPJS
```

---

## Transaction Number Format

### Payslip Number
```
GJ.MM.YYYY/DDD/NNN
```
| Part | Description | Example |
|------|-------------|---------|
| GJ | Fixed prefix (Gaji) | GJ |
| MM | Month (01-12) | 07 |
| YYYY | Year | 2026 |
| DDD | Department code (3-5 chars) | SALES |
| NNN | Sequence per month per dept | 001 |

Example: `GJ.07.2026/SALES/001` = Gaji Juli 2026, Sales, slip ke-1

### THR Number
```
THR.YYYY/DDD/NNN
```

---

## Security Model

### Groups (4-Level)

```
l10n_id_hr_payroll.group_hr_user (Pegawai)
    └── l10n_id_hr_payroll.group_hr_admin (Admin HR)
            └── l10n_id_hr_payroll.group_hr_supervisor (Supervisor)
                    └── l10n_id_hr_payroll.group_hr_full_admin (Full Administrator)
```

### ACL Summary

| Model | User | Admin | Supervisor | Full Admin |
|-------|------|-------|------------|------------|
| hr.payslip | R | R/W/C | R/W/C | R/W/C/U |
| hr.overtime | R | R/W/C | R/W/C | R/W/C/U |
| hr.thr | R | R/W/C | R/W/C | R/W/C/U |
| hr.bpjs | R | R/W/C | R/W/C | R/W/C/U |
| hr.bpjs.rate | — | R/W/C | R/W/C | R/W/C/U |
| hr.bpjs.submission | — | R/W/C | R/W/C | R/W/C/U |
| hr.ebupot | — | R/W/C | R/W/C | R/W/C/U |
| hr.spt.tahunan | — | R/W/C | R/W/C | R/W/C/U |
| hr.shift.type | — | R/W/C | R/W/C | R/W/C/U |
| hr.shift.rotation | — | R/W/C | R/W/C | R/W/C/U |
| hr.shift.assign | — | R/W/C | R/W/C | R/W/C/U |
| hr.shift.daily | — | R/W/C | R/W/C | R/W/C/U |
| hr.payroll.dashboard | — | R/C | R/C | R/C |
| hr.user.dashboard | R/C | R/C | R/C | R/C |

---

## PPh 21 Calculation Flow

```
Penghasilan Bruto (gaji + tunj + bonus + lembur)
        ↓ × 12
Penghasilan Bruto Setahun
        ↓ - Biaya Jabatan (5%, maks Rp 6jt)
        ↓ - JHT karyawan (2%)
        ↓ - JP karyawan (1%)
Penghasilan Neto Setahun
        ↓ - PTKP (sesuai status)
PKP Setahun (dibulatkan ke ribuan ke bawah)
        ↓ tarif progresif (5/15/25/30/35%)
PPh 21 Tahunan
        ↓ ÷ 12
PPh 21 Bulanan
        ↓ + surcharge 20% (jika tidak ada NPWP)
PPh 21 Final
```

---

## BPJS Rates

| Komponen | Karyawan | Perusahaan | Cap Upah |
|----------|----------|------------|----------|
| BPJS Kesehatan | 1% | 4% | Rp 12.000.000 |
| JHT | 2% | 3.7% | — |
| JP | 1% | 2% | Rp 9.077.600 |
| JKK | 0% | 0.24–1.74% | — |
| JKM | 0% | 0.30% | — |

---

## Attendance Device Integration

### Supported Brands

| Brand | Connection | Protocol | Status |
|-------|-----------|----------|--------|
| ZKTeco | TCP/UDP Direct | PyZK (port 4370) | Implemented |
| ZKTeco | ADMS Push | HTTP (port 8068) | Implemented |
| Solution | SOAP/HTTP | requests (port 80) | Planned |
| Fingerspot | TCP/UDP | PyZK compatible | Implemented |
| ATT2000 | CSV Import | File upload | Implemented |
| eSSL | CSV Import | File upload | Implemented |
| Generic | CSV/Excel | File upload | Implemented |

### Employee Matching

Matches device User ID to Odoo employee via:
- `pin` field (default)
- `identification_id` field

Configurable per device in the device registry.

---

## Trial Mode (Bypass-Proof)

### 3-Layer Verification

```
Layer 1: ir.config_parameter (install date + SHA-256 checksum)
Layer 2: Earliest hr.payslip.create_date (DB timestamp)
Layer 3: Earliest hr.thr.create_date (cross-validation)
```

### Behavior

| State | User Sees | Can Do |
|-------|-----------|--------|
| Trial Active (day 1-5) | Full access, "Sisa X hari" banner | Everything |
| Trial Expired (day 6+) | "Masa uji coba berakhir" banner | READ-ONLY |

### Blocked Operations (when expired)

- `hr.payslip.create()` — new payslip
- `hr.payslip.action_compute()` — compute salary
- `hr.payslip.action_confirm()` — confirm payslip
- `hr.payslip.generate.wizard` — bulk payslip
- `hr.thr.create()` — new THR
- `hr.thr.wizard` — bulk THR
- `hr.overtime.create()` — new overtime
- `hr.overtime.action_submit()` — submit overtime

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
