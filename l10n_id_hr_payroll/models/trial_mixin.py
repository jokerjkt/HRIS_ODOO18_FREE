# -*- coding: utf-8 -*-
"""
Trial Mixin — Bypass-proof trial period check
==============================================
3-layer verification:
  1. ir.config_parameter (install date + SHA-256 checksum)
  2. Earliest hr.payslip.create_date (DB timestamp, can't be faked)
  3. Earliest hr.thr.create_date (cross-validation)

Bilingual messages: Indonesian + English
"""
import hashlib
from datetime import date

from odoo import models, api
from odoo.exceptions import UserError

TRIAL_DAYS = 5
_SECRET = 'a]3$x7K!mP2vQ9wR!z#L'

TRIAL_EXPIRED_MSG = (
    '⚠️ Masa uji coba modul HR Payroll Indonesia sudah berakhir.\n'
    'Trial period for Indonesian HR Payroll module has expired.\n\n'
    f'Fitur terbatas selama {TRIAL_DAYS} hari sejak instalasi.\n'
    f'Features are limited for {TRIAL_DAYS} days from installation.\n\n'
    'Untuk lisensi penuh, silakan hubungi:\n'
    'For full license, please contact:\n'
    '📧 Email: susilo.cdv@gmail.com\n'
    '🔗 LinkedIn: linkedin.com/in/susilo-raden-68a19049'
)


class TrialMixin(models.AbstractModel):
    _name = 'trial.mixin'
    _description = 'Trial Period Check — Bypass-Proof'

    @api.model
    def _compute_trial_hash(self, date_str):
        """Generate tamper-proof SHA-256 hash."""
        raw = f"{date_str}:{_SECRET}:{self.env.cr.dbname}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @api.model
    def _get_trial_install_date(self):
        """Get install date from ir.config_parameter."""
        return self.env['ir.config_parameter'].get_param(
            'l10n_id_hr_payroll.trial_install_date'
        )

    @api.model
    def _is_trial_active(self):
        """3-layer trial verification — bypass-proof."""
        # Layer 1: ir.config_parameter + checksum
        install_date_str = self._get_trial_install_date()
        if not install_date_str:
            return True  # Not installed yet

        stored_hash = self.env['ir.config_parameter'].get_param(
            'l10n_id_hr_payroll.trial_hash'
        )
        expected_hash = self._compute_trial_hash(install_date_str)
        if stored_hash != expected_hash:
            return False  # Tampering detected

        # Layer 2: earliest payslip create_date (DB timestamp)
        self.env.cr.execute("""
            SELECT create_date FROM hr_payslip
            ORDER BY create_date ASC LIMIT 1
        """)
        row = self.env.cr.fetchone()
        if row:
            earliest_payslip = row[0]
            if hasattr(earliest_payslip, 'date'):
                earliest_payslip = earliest_payslip.date()
            days_from_payslip = (date.today() - earliest_payslip).days
            if days_from_payslip > TRIAL_DAYS:
                return False

        # Layer 3: earliest THR create_date
        self.env.cr.execute("""
            SELECT create_date FROM hr_thr
            ORDER BY create_date ASC LIMIT 1
        """)
        row = self.env.cr.fetchone()
        if row:
            earliest_thr = row[0]
            if hasattr(earliest_thr, 'date'):
                earliest_thr = earliest_thr.date()
            days_from_thr = (date.today() - earliest_thr).days
            if days_from_thr > TRIAL_DAYS:
                return False

        # Layer 4: install date check
        install_date = date.fromisoformat(install_date_str)
        days_elapsed = (date.today() - install_date).days
        return days_elapsed <= TRIAL_DAYS

    @api.model
    def _enforce_trial(self):
        """Raise error if trial expired. Call in every write operation."""
        if not self._is_trial_active():
            raise UserError(TRIAL_EXPIRED_MSG)

    @api.model
    def _get_trial_info(self):
        """Return trial status info for dashboard display."""
        install_date_str = self._get_trial_install_date()
        if not install_date_str:
            return {
                'days_left': TRIAL_DAYS,
                'expired': False,
                'install_date': False,
                'message': '',
            }

        install_date = date.fromisoformat(install_date_str)
        days_elapsed = (date.today() - install_date).days
        days_left = max(0, TRIAL_DAYS - days_elapsed)
        expired = days_left <= 0

        message = ''
        if expired:
            message = TRIAL_EXPIRED_MSG
        elif days_left <= 2:
            message = (
                f'⚠️ Sisa masa uji coba: {days_left} hari\n'
                f'Trial days remaining: {days_left}\n'
                'Hubungi vendor untuk lisensi penuh.\n'
                'Contact vendor for full license.\n'
                '📧 susilo.cdv@gmail.com'
            )

        return {
            'days_left': days_left,
            'expired': expired,
            'install_date': install_date_str,
            'message': message,
        }
