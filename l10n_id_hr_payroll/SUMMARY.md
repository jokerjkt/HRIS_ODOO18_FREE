# Indonesian HR Payroll System — Odoo 18

**Modul HR Payroll Indonesia untuk Odoo 18 Community**
Integrated HR payroll solution for Indonesian companies.

*Last updated: 2026-07-23 (Phase 7: Bug Fixes, Odoo 18 Compatibility)*

---

## Overview

Complete HR payroll system built as a standalone module for Odoo 18 Community (no Enterprise dependencies). Fully integrated with Odoo 18's standard HR app — appears as native sub-menus under the Employees app.

### Features

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
| 10 | **Dashboard Personal** | Employee self-service dashboard |
| 11 | **Bank Payment** | List view + PDF report for bank transfer |
| 12 | **Reports** | Slip Gaji PDF, Bukti Potong 1721, Rekap BPJS |
| 13 | **Trial Mode** | 5-day bypass-proof trial, read-only after expiry |
| 14 | **Demo Data** | Sample employees, contracts ready to test |
| 15 | **Shift Scheduling** | 3-shift weekly / 4-shift daily rotation with Gantt view |
| 16 | **Bulk Shift Assign** | Wizard to assign shifts to multiple employees |
| 17 | **Holiday Integration** | Auto-detect public holidays from hr.holiday |
| 18 | **Role/Group System** | 4-level security (Pegawai → Admin → Supervisor → Full Admin) |
| 19 | **Attendance Device Integration** | Multi-brand support: ZKTeco, Solution, Fingerspot, ATT2000 |
| 20 | **CSV/Excel Import** | Universal import from any attendance machine |
| 21 | **ZKTeco Direct** | TCP/UDP connection via PyZK library |
| 22 | **ADMS Cloud Push** | Flask server for ZKTeco push data |
| 23 | **Device Registry** | Manage multiple attendance machines |
| 24 | **Attendance Log Viewer** | View and match raw attendance logs |
| 25 | **Geo-Fence** | Multi-location attendance zones with GPS verification |
| 26 | **Data Isolation** | Record rules for payslip/THR/attendance |
| 27 | **API Key Auth** | Flask ADMS secured with API key |
| 28 | **Mobile PWA** | Selfie check-in with GPS and camera |
| 29 | **e-Bupot** | Electronic withholding tax document |
| 30 | **SPT Tahunan** | Annual tax return data |
| 31 | **E-Filing DJP** | Direct submission to DJP Online |
| 32 | **BPJS Submission** | CSV export for BPJS portal upload |
| 33 | **Unit Tests** | 42+ tests covering all modules |

---

## Installation

### Prerequisites

- Odoo 18 Community (tested with Odoo 18.0)
- Python 3.10+
- PostgreSQL 14+
- Docker (optional, for containerized deployment)

### Option 1: Docker Installation (Recommended)

#### 1. Clone the repository
```bash
git clone https://github.com/jokerjkt/HRIS_ODOO18.git
# or for free version:
git clone https://github.com/jokerjkt/HRIS_ODOO18_FREE.git
```

#### 2. Copy module to addons
```bash
cp -r HRIS_ODOO18/l10n_id_hr_payroll /path/to/odoo/addons/
# or sync via rsync:
rsync -av --delete l10n_id_hr_payroll/ /path/to/docker/addons/l10n_id_hr_payroll/
```

#### 3. Configure Odoo
Edit `odoo.conf`:
```ini
[options]
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
db_name = odoo_test
admin_passwd = admin
```

#### 4. Start Docker containers
```bash
docker-compose up -d
```

#### 5. Install module
1. Open browser: `http://localhost:8069`
2. Login: `admin` / `admin`
3. Go to **Apps** → **Update Apps List**
4. Search "Indonesian HR Payroll"
5. Click **Install**

### Option 2: Direct Installation

#### 1. Copy module
```bash
cp -r l10n_id_hr_payroll /path/to/odoo/addons/
```

#### 2. Restart Odoo
```bash
./odoo-bin -c /path/to/odoo.conf -d your_database
```

#### 3. Install module
1. Open browser: `http://localhost:8069`
2. Go to **Apps** → **Update Apps List**
3. Search "Indonesian HR Payroll"
4. Click **Install**

### Option 3: Docker with docker-compose.yml

```yaml
version: '3.8'
services:
  odoo:
    image: odoo:18.0
    depends_on:
      - db
    ports:
      - "8069:8069"
    volumes:
      - odoo-data:/var/lib/odoo
      - ./addons:/mnt/extra-addons
      - ./config:/etc/odoo
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - db-data:/var/lib/postgresql/data

volumes:
  odoo-data:
  db-data:
```

Start with:
```bash
docker-compose up -d
```

---

## Usage Guide

### 1. Setup Karyawan

1. Go to **Employees** → select employee
2. Click **Indonesia HR** tab
3. Fill in:
   - **NIK** (Nomor Induk Kependudukan)
   - **NPWP** (Nomor Pokok Wajib Pajak)
   - **PTKP** status (TK/0, TK/1, K/0, K/1, etc.)
   - **BPJS** info (class, family members)
   - **Bank** details (account number, bank name)

### 2. Setup Kontrak

1. Go to **Employees** → **Contracts**
2. Create or edit contract
3. Fill in:
   - **Gaji Pokok** (basic salary)
   - **Tunjangan Tetap** (fixed allowance)
   - **Tunjangan Tidak Tetap** (variable allowance)

### 3. Proses Payroll

1. Go to **Employees** → **Payroll** → **Daftar Slip Gaji**
2. Click **New**
3. Select employee and period
4. Click **Hitung Gaji** (Compute Salary)
5. PPh 21 & BPJS auto-calculated
6. Review tabs: PPh 21 | BPJS | Lembur | THR
7. Click **Konfirmasi** → Done

### 4. Bulk Payslip Generation

1. Go to **Employees** → **Payroll** → **Buat Slip Gaji Massal**
2. Select period, filter departments/employees
3. Preview count and estimated total
4. Click **Buat Slip Gaji** → Auto-compute all

### 5. Lembur (Overtime)

1. Go to **Employees** → **Lembur** → **Pengajuan Lembur Saya**
2. Click **New**
3. Fill date, hours, activity description
4. Click **Submit ke Atasan**
5. Manager reviews in **Perlu Persetujuan**
6. Approved overtime → auto-linked to payslip

### 6. THR

1. Go to **Employees** → **THR** → **Daftar THR**
2. Click **Generate THR Massal**
3. Fill year, holiday, payment date
4. Preview eligible employees
5. Click **Generate THR** → Confirm → Mark paid

### 7. Shift Scheduling

1. **Configuration** → **Tipe Shift** — Define shift types (Pagi/Siang/Malam/Libur)
2. **Configuration** → **Pola Rotasi Shift** — Create rotation patterns
3. **Shift Scheduling** → **Assign Shift** — Assign rotation to employee
4. **Shift Scheduling** → **Generate Bulk Assign** — Assign to multiple employees
5. **Shift Scheduling** → **Jadwal Harian** — View Gantt/Calendar schedule

### 8. Attendance Device Integration

1. **Mesin Absensi** → **Daftar Mesin** — Add attendance machine
2. Select brand (ZKTeco/Solution/Fingerspot/ATT2000)
3. For CSV Import: Set connection type to "File Import Only"
4. **Mesin Absensi** → **Import Absensi** — Import from file or pull from device
5. Upload CSV/Excel → Parse → Preview → Import
6. **Mesin Absensi** → **Log dari Mesin** — View raw logs and match employees

### 9. Mobile PWA Attendance

1. Open Odoo on mobile browser
2. Login with your credentials
3. Go to **Absensi Mobile** menu
4. Allow camera and GPS permissions
5. Take selfie and submit
6. System auto-detects check-in/check-out

### 10. e-Bupot & SPT Tahunan

1. **Payroll** → **Daftar Slip Gaji** → select payslip
2. Click **Generate e-Bupot** action
3. Review withholding tax data
4. Submit via **E-Filing DJP** wizard
5. Download receipt/proof

### 11. BPJS Submission

1. Go to **Reporting** → **Rekap Iuran BPJS**
2. Review BPJS contribution data
3. Click **Generate Submission**
4. Upload CSV to BPJS portal

### 12. Cetak Laporan

- **Slip Gaji**: from Payslip → Print → Slip Gaji Indonesia
- **Bukti Potong**: from Payslip → Print → Bukti Potong PPh 21
- **Rekap BPJS**: from menu → Rekap Iuran BPJS
- **Bank Payment**: from Payroll → Daftar Pembayaran Gaji → Print

---

## Menu Reference

### HR App (Employees)

| Menu | Path | Description |
|------|------|-------------|
| Dashboard Saya | HR → Dashboard Saya | Personal employee dashboard |
| Dashboard HR | HR → Dashboard HR | HR team dashboard |
| Dashboard Admin | HR → Dashboard Admin | Admin dashboard with full stats |

### Payroll

| Menu | Path | Description |
|------|------|-------------|
| Daftar Slip Gaji | HR → Payroll → Daftar Slip Gaji | List of all payslips |
| Daftar Pembayaran Gaji | HR → Payroll → Daftar Pembayaran Gaji | Bank payment list |
| Buat Slip Gaji Massal | HR → Payroll → Buat Slip Gaji Massal | Bulk payslip wizard |

### Lembur (Overtime)

| Menu | Path | Description |
|------|------|-------------|
| Pengajuan Lembur Saya | HR → Lembur → Pengajuan Lembur Saya | Employee overtime requests |
| Perlu Persetujuan | HR → Lembur → Perlu Persetujuan | Pending approval |
| Semua Lembur | HR → Lembur → Semua Lembur | All overtime records |

### THR

| Menu | Path | Description |
|------|------|-------------|
| Daftar THR | HR → THR → Daftar THR | THR records list |
| Generate THR Massal | HR → THR → Generate THR Massal | Bulk THR wizard |
| THR Saya | HR → THR Saya | Employee THR view |

### Shift Scheduling

| Menu | Path | Description |
|------|------|-------------|
| Jadwal Harian | HR → Shift Scheduling → Jadwal Harian | Gantt/Calendar/List view |
| Assign Shift | HR → Shift Scheduling → Assign Shift | Individual assignment |
| Generate Bulk Assign | HR → Shift Scheduling → Generate Bulk Assign | Bulk assignment wizard |

### Attendance (Attendances App)

| Menu | Path | Description |
|------|------|-------------|
| Daftar Mesin | Attendances → Mesin Absensi → Daftar Mesin | Device registry |
| Log dari Mesin | Attendances → Mesin Absensi → Log dari Mesin | Raw attendance logs |
| Import Absensi | Attendances → Mesin Absensi → Import Absensi | Import from file |
| Geo-Fence Lokasi | Attendances → Mesin Absensi → Geo-Fence Lokasi | GPS zones |
| Absensi Mobile | Attendances → Absensi Mobile | Selfie check-in |

### Reporting

| Menu | Path | Description |
|------|------|-------------|
| Rekap Iuran BPJS | Reporting → Rekap Iuran BPJS | BPJS summary |

### Configuration

| Menu | Path | Description |
|------|------|-------------|
| Tipe Shift | Configuration → Tipe Shift | Shift type definitions |
| Pola Rotasi Shift | Configuration → Pola Rotasi Shift | Rotation patterns |
| Tarif BPJS | Configuration → Tarif BPJS | BPJS rate config |

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

## Trial Mode

- **Duration**: 5 days from installation
- **Bypass-proof**: 3-layer verification (config + checksum + DB timestamps)
- **After expiry**: Read-only mode (can view data, cannot create/edit/compute)
- **Bilingual**: Indonesian + English messages

---

## Contact

- **Email**: susilo.cdv@gmail.com
- **LinkedIn**: [Susilo Raden](https://www.linkedin.com/in/susilo-raden-68a19049)
- **GitHub Free**: https://github.com/jokerjkt/HRIS_ODOO18_FREE
- **GitHub Pro**: https://github.com/jokerjkt/HRIS_ODOO18
