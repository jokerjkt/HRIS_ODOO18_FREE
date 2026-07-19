# -*- coding: utf-8 -*-
{
    'name': 'Indonesian HR Payroll (PPh 21 & BPJS)',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Payroll Indonesia: PPh 21, BPJS, Lembur, THR, Shift Scheduling, Dashboard',
    'description': """
Modul HR Payroll Indonesia untuk Odoo 18
=========================================
Fitur utama:
- PPh 21 otomatis (tarif progresif 5%-35%)
- BPJS Ketenagakerjaan (JKK, JKM, JHT, JP)
- BPJS Kesehatan
- Manajemen Lembur dengan validasi atasan
- Perhitungan THR (Tunjangan Hari Raya)
- Jenis cuti sesuai regulasi Indonesia
- Slip gaji format Indonesia
- Bukti Potong 1721-A1/A2
- Rekap iuran BPJS
- Dashboard pribadi untuk setiap karyawan
- Shift Scheduling dengan rotasi (3-shift weekly, 4-shift daily)
- Bulk Assign Shift ke banyak karyawan
- Gantt view jadwal shift harian
- Sistem role/grup 4 tingkat
    """,
    'author': 'Susilo Raden',
    'website': 'https://www.linkedin.com/in/susilo-raden-68a19049',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_contract',
        'hr_work_entry',
        'hr_attendance',
        'hr_holidays',
        'hr_expense',
        'mail',
    ],
    'data': [
        # Security (groups first, then ACLs)
        'security/hr_role_security.xml',
        'security/hr_overtime_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/hr_bpjs_rate_data.xml',
        'data/hr_leave_type_data.xml',
        'data/hr_sequence_data.xml',
        'data/hr_shift_type_data.xml',
        # Views (order matters: define actions before they are referenced)
        'views/hr_employee_views.xml',
        'views/hr_department_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_payment_views.xml',
        'views/hr_overtime_views.xml',
        'views/hr_thr_views.xml',
        'views/hr_bpjs_rate_views.xml',
        # Shift Scheduling views (daily BEFORE assign because assign references daily action)
        'views/hr_shift_type_views.xml',
        'views/hr_shift_rotation_views.xml',
        'views/hr_shift_daily_views.xml',
        'views/hr_shift_assign_views.xml',
        # Reports (define report actions)
        'report/hr_payslip_report.xml',
        'report/hr_bukti_potong_report.xml',
        'report/hr_bpjs_report.xml',
        'report/hr_bank_payment_report.xml',
        # Wizards (define wizard actions)
        'wizard/hr_thr_wizard_views.xml',
        'wizard/hr_payslip_generate_views.xml',
        'wizard/hr_shift_bulk_assign_views.xml',
        # Personal Dashboard
        'views/hr_my_dashboard_views.xml',
        # HR User Dashboard (references actions above)
        'views/hr_user_dashboard_views.xml',
        # Dashboard Admin (references all actions above)
        'views/dashboard_views.xml',
        # Menu (references all actions above)
        'views/menu_views.xml',
        # Security (ACL for TransientModel — loaded after Python models)
        'security/hr_payroll_security.xml',
    ],
    'demo': [
        'data/hr_demo_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
