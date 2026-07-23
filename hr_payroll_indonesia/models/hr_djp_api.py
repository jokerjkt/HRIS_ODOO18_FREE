# -*- coding: utf-8 -*-
"""
DJP API Configuration & Connector
==================================
Konfigurasi dan koneksi ke API Direktorat Jenderal Pajak (Coretax).
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta

import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrDjpApiConfig(models.Model):
    _name = 'hr.djp.api.config'
    _description = 'Konfigurasi API DJP'

    name = fields.Char(string='Nama', required=True, default='DJP Coretax')
    api_url = fields.Char(
        string='API URL',
        default='https://api-djp.pajak.go.id',
        help='URL API DJP (Prod: api-djp.pajak.go.id)',
    )
    npwp = fields.Char(string='NPWP Perusahaan (15 digit)', required=True)
    efin = fields.Char(string='EFIN', required=True)
    username = fields.Char(string='Username DJP Online')
    password = fields.Char(string='Password DJP Online')
    token = fields.Text(string='Access Token', readonly=True)
    token_expiry = fields.Datetime(string='Token Expiry', readonly=True)
    is_active = fields.Boolean(string='Aktif', default=True)
    environment = fields.Selection([
        ('sandbox', 'Sandbox (Testing)'),
        ('production', 'Produksi'),
    ], string='Environment', default='sandbox')

    _sql_constraints = [
        ('npwp_uniq', 'unique(npwp)', 'NPWP sudah terdaftar!'),
    ]

    def action_test_connection(self):
        """Test koneksi ke DJP API."""
        self.ensure_one()
        try:
            resp = requests.get(f'{self.api_url}/', timeout=10)
            if resp.status_code == 200:
                raise UserError(f'Koneksi berhasil! Response: {resp.text[:100]}')
            else:
                raise UserError(f'Koneksi gagal. Status: {resp.status_code}')
        except requests.exceptions.ConnectionError:
            raise UserError('Tidak dapat terhubung ke server DJP. Periksa koneksi internet.')
        except requests.exceptions.Timeout:
            raise UserError('Timeout — server DJP tidak merespon.')

    def action_get_token(self):
        """Ambil access token dari DJP API."""
        self.ensure_one()
        try:
            raw = f"{self.username}:{self.password}"
            auth_header = hashlib.sha256(raw.encode()).hexdigest()

            resp = requests.post(
                f'{self.api_url}/ctas/genToken',
                json={
                    'username': self.username,
                    'password': self.password,
                },
                headers={'Content-Type': 'application/json'},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.write({
                    'token': data.get('token', ''),
                    'token_expiry': datetime.now() + timedelta(hours=24),
                })
                raise UserError('Token berhasil diambil!')
            else:
                raise UserError(f'Gagal ambil token. Status: {resp.status_code}\n{resp.text[:200]}')
        except requests.exceptions.ConnectionError:
            raise UserError('Tidak dapat terhubung ke server DJP.')
        except requests.exceptions.Timeout:
            raise UserError('Timeout — server DJP tidak merespon.')


class HrDjpApiConnector(models.AbstractModel):
    _name = 'hr.djp.api.connector'
    _description = 'DJP API Connector'

    @api.model
    def _get_config(self):
        config = self.env['hr.djp.api.config'].search([('is_active', '=', True)], limit=1)
        if not config:
            raise UserError(
                'Konfigurasi DJP API belum diatur.\n'
                'Email: susilo.cdv@gmail.com'
            )
        return config

    @api.model
    def _get_headers(self):
        config = self._get_config()
        return {
            'Authorization': f'Bearer {config.token}',
            'Content-Type': 'application/json',
        }

    @api.model
    def submit_ebupot(self, ebupot_data):
        """Submit e-Bupot ke DJP."""
        config = self._get_config()
        if not config.token or config.token_expiry < fields.Datetime.now():
            config.action_get_token()

        try:
            resp = requests.post(
                f'{config.api_url}/ebupot/submit',
                json=ebupot_data,
                headers=self._get_headers(),
                timeout=60,
            )
            return resp.json()
        except Exception as e:
            _logger.error("DJP API submit error: %s", str(e))
            return {'error': str(e)}

    @api.model
    def check_status(self, reference):
        """Cek status submission ke DJP."""
        config = self._get_config()
        if not config.token or config.token_expiry < fields.Datetime.now():
            config.action_get_token()

        try:
            resp = requests.get(
                f'{config.api_url}/status/{reference}',
                headers=self._get_headers(),
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            _logger.error("DJP API status check error: %s", str(e))
            return {'error': str(e)}
