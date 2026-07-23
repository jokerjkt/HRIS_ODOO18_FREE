# -*- coding: utf-8 -*-
"""
Pro License Module
==================
Disables trial restrictions when installed.
"""
from odoo import models, api


class ProLicense(models.Model):
    _inherit = 'trial.mixin'

    @api.model
    def _is_trial_active(self):
        """Pro version: trial is always active (no expiration)."""
        if self.env['ir.module.module'].search_count([
            ('name', '=', 'hr_payroll_indonesia_pro'),
            ('state', '=', 'installed'),
        ]):
            return True
        return super()._is_trial_active()
