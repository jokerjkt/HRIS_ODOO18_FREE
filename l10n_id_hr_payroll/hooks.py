# -*- coding: utf-8 -*-
"""
Post-init hook:
1. Store trial install date + checksum (bypass-proof)
2. Set default department codes for existing departments.
"""
import logging
from datetime import date

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    After module installation:
    1. Store trial install date with SHA-256 hash (bypass-proof)
    2. Set default codes for departments that don't have one yet.
    """
    # ── 1. Store trial install date + hash ──────────────────────────────────
    today_str = date.today().isoformat()
    # Compute hash using the same logic as trial_mixin
    # Read secret from config parameter (single source of truth)
    secret = env['ir.config_parameter'].get_param(
        'l10n_id_hr_payroll.trial_secret', 'a]3$x7K!mP2vQ9wR!z#L'
    )
    raw = f"{today_str}:{secret}:{env.cr.dbname}"
    import hashlib
    hash_val = hashlib.sha256(raw.encode()).hexdigest()

    env['ir.config_parameter'].set_param(
        'l10n_id_hr_payroll.trial_install_date', today_str
    )
    env['ir.config_parameter'].set_param(
        'l10n_id_hr_payroll.trial_hash', hash_val
    )
    _logger.info('Trial install date set: %s (hash: %s...)', today_str, hash_val[:16])

    # ── 2. Set default department codes ─────────────────────────────────────
    DEPT_CODES = {
        'Administration': 'ADM',
        'Management': 'MGMT',
        'Sales': 'SALES',
        'Research & Development': 'RND',
        'R&D USA': 'RND2',
        'Long Term Projects': 'LTP',
        'Professional Services': 'PSVC',
    }

    departments = env['hr.department'].search([('code', '=', False)])
    for dept in departments:
        dept_name = dept.name
        if isinstance(dept_name, dict):
            dept_name = dept_name.get('en_US', dept_name.get('id_ID', ''))
        code = DEPT_CODES.get(dept_name)
        if not code and dept_name:
            code = dept_name[:3].upper()
        if code:
            dept.write({'code': code})
            _logger.info('Set department code: %s -> %s', dept_name, code)
