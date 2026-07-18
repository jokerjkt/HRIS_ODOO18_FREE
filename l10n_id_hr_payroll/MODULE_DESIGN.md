# MODULE_DESIGN.md — Desain Teknis Modul `l10n_id_hr_payroll`

## Overview Arsitektur

```
┌─────────────────────────────────────────────────────────┐
│                    Odoo 18 Core                         │
│  hr  │  hr_contract  │  hr_work_entry  │  hr_holidays  │
└──────────────────────┬──────────────────────────────────┘
                       │ extends / inherit
                       ▼
┌─────────────────────────────────────────────────────────┐
│            l10n_id_hr_payroll (Module Kita)             │
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
│  │  Trial Mixin (bypass-proof, 3-layer check)      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Reports: Slip Gaji | Bukti Potong | Rekap BPJS │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Model Design

### Extension Models (inherit from Odoo core)

| Model | Inherits | Fields Added |
|-------|----------|--------------|
| `hr.employee` | `hr.employee` | NIK, NPWP, PTKP, BPJS TK/Kes, bank info, join_date |
| `hr.department` | `hr.department` | code (for payslip numbering) |
| `hr.contract` | `hr.contract` | x_tunjangan_tetap, x_tunjangan_tidak_tetap |

### Standalone Models (custom _name)

| Model | Description | Inherits |
|-------|-------------|----------|
| `hr.payslip` | Payslip (GJ.MM.YYYY/DDD/NNN) | mail.thread, trial.mixin |
| `hr.pph21` | PPh 21 calculation detail | — |
| `hr.bpjs` | BPJS contribution detail | — |
| `hr.bpjs.rate` | BPJS rate config by risk class | — |
| `hr.overtime` | Overtime with approval workflow | mail.thread, mail.activity.mixin, trial.mixin |
| `hr.thr` | THR (holiday allowance) | mail.thread, trial.mixin |
| `hr.payroll.dashboard` | Admin dashboard | — |
| `hr.user.dashboard` | HR User dashboard | — |

### TransientModels (wizards)

| Model | Description |
|-------|-------------|
| `hr.thr.wizard` | Bulk THR generation |
| `hr.payslip.generate.wizard` | Bulk payslip generation |
| `hr.overtime.reject.wizard` | Overtime rejection reason |

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

## Transaction Number Format

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

---

## Security Model

### Groups

```
hr.group_hr_user
    └── hr.group_hr_manager
            └── group_hr_overtime_user
                    └── group_hr_overtime_manager
```

### ACL Summary

| Model | User | Manager |
|-------|------|---------|
| hr.payslip | R/W/C | R/W/C/U |
| hr.overtime | R/W/C | R/W/C/U |
| hr.thr | R | R/W/C/U |
| hr.bpjs | R/W/C | R/W/C/U |
| hr.bpjs.rate | R | R/W/C/U |
| hr.payroll.dashboard | — | R/C |
| hr.user.dashboard | R/C | R/C |

---

## Alur Data Payroll End-to-End

```
1. Data Karyawan (NIK, NPWP, PTKP, BPJS class, join_date)
         ↓
2. Kontrak (gaji pokok, tunjangan tetap/tidak tetap)
         ↓
3. Lembur Approved → linked ke payslip
         ↓
4. Create Payslip → set periode → auto-number GJ.MM.YYYY/DDD/NNN
         ↓
5. Compute Sheet:
   a. BPJS Engine: hitung JHT/JP/JKK/JKM/Kes → simpan hr.bpjs
   b. PPh 21 Engine: hitung PKP → tarif progresif → simpan hr.pph21
         ↓
6. Review tabs: PPh 21 | BPJS | Lembur | THR
         ↓
7. Confirm Payslip → state = done
         ↓
8. Print:
   - Slip Gaji (PDF)
   - Bukti Potong 1721-A1/A2 (PDF)
   - Rekap BPJS (PDF)
   - Daftar Pembayaran Bank (PDF)
```

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

## Contact

- **Email**: susilo.cdv@gmail.com
- **LinkedIn**: [Susilo Raden](https://www.linkedin.com/in/susilo-raden-68a19049)

---

*Last updated: 2026-07-18*
