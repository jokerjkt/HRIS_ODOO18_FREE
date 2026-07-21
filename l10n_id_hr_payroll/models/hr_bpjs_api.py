# -*- coding: utf-8 -*-
"""
BPJS API Configuration & Connectors
====================================
Konfigurasi dan koneksi ke API BPJS Ketenagakerjaan & Kesehatan.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta

import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrBpjsApiConfig(models.Model):
    _name = 'hr.bpjs.api.config'
    _description = 'Konfigurasi API BPJS'
    _inherit = ['trial.mixin']

    name = fields.Char(string='Nama', required=True)
    service_type = fields.Selection([
        ('tk', 'BPJS Ketenagakerjaan'),
        ('kes', 'BPJS Kesehatan'),
    ], string='Jenis Layanan', required=True)
    api_url = fields.Char(string='API URL', required=True)
    client_id = fields.Char(string='Client ID / Cons ID')
    client_secret = fields.Char(string='Client Secret / Secret Key')
    user_key = fields.Char(string='User Key', help='Untuk BPJS TK')
    company_bpjs_no = fields.Char(string='No. Peserta Perusahaan')
    token = fields.Text(string='Access Token', readonly=True)
    token_expiry = fields.Datetime(string='Token Expiry', readonly=True)
    is_active = fields.Boolean(string='Aktif', default=True)
    environment = fields.Selection([
        ('sandbox', 'Sandbox'),
        ('production', 'Produksi'),
    ], string='Environment', default='sandbox')

    def action_test_connection(self):
        self.ensure_one()
        try:
            resp = requests.get(f'{self.api_url}/', timeout=10)
            raise UserError(f'Koneksi OK. Status: {resp.status_code}')
        except requests.exceptions.ConnectionError:
            raise UserError('Tidak dapat terhubung ke server BPJS.')
        except requests.exceptions.Timeout:
            raise UserError('Timeout — server BPJS tidak merespon.')

    def action_get_token(self):
        self.ensure_one()
        try:
            auth_str = f"{self.client_id}:{self.client_secret}"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            resp = requests.post(
                f'{self.api_url}/token',
                data={'grant_type': 'client_credentials'},
                headers=headers,
                auth=(self.client_id, self.client_secret),
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.write({
                    'token': data.get('access_token', ''),
                    'token_expiry': datetime.now() + timedelta(seconds=data.get('expires_in', 3600)),
                })
                raise UserError('Token berhasil diambil!')
            else:
                raise UserError(f'Gagal ambil token. Status: {resp.status_code}\n{resp.text[:200]}')
        except requests.exceptions.ConnectionError:
            raise UserError('Tidak dapat terhubung ke server BPJS.')


class HrBpjsApiConnector(models.AbstractModel):
    _name = 'hr.bpjs.api.connector'
    _description = 'BPJS API Connector (Abstract)'

    @api.model
    def _get_config(self, service_type):
        config = self.env['hr.bpjs.api.config'].search([
            ('service_type', '=', service_type),
            ('is_active', '=', True),
        ], limit=1)
        if not config:
            raise UserError(
                f'Konfigurasi API {"BPJS Ketenagakerjaan" if service_type == "tk" else "BPJS Kesehatan"} belum diatur.\n'
                'Email: susilo.cdv@gmail.com'
            )
        return config

    @api.model
    def _get_headers(self, config):
        return {
            'Authorization': f'Bearer {config.token}',
            'Content-Type': 'application/json',
            'Cons-ID': config.client_id or '',
        }

    @api.model
    def authenticate(self, service_type):
        config = self._get_config(service_type)
        config.action_get_token()

    @api.model
    def check_participant(self, bpjs_no, service_type):
        raise UserError('Method harus dioverride oleh child class.')

    @api.model
    def submit_contribution(self, data, service_type):
        raise UserError('Method harus dioverride oleh child class.')


class HrBpjsTkConnector(models.Model):
    _name = 'hr.bpjs.tk.connector'
    _description = 'BPJS Ketenagakerjaan API Connector'
    _inherit = 'hr.bpjs.api.connector'

    @api.model
    def check_participant(self, bpjs_tk_no):
        """Cek kepesertaan BPJS TK."""
        config = self._get_config('tk')
        if not config.token or config.token_expiry < fields.Datetime.now():
            self.authenticate('tk')

        try:
            resp = requests.get(
                f'{config.api_url}/api/employe/findByNik/{bpjs_tk_no}',
                headers=self._get_headers(config),
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            _logger.error("BPJS TK check error: %s", str(e))
            return {'error': str(e)}

    @api.model
    def submit_contribution(self, employee_data_list):
        """Submit kontribusi BPJS TK (JKK, JKM, JHT, JP)."""
        config = self._get_config('tk')
        if not config.token or config.token_expiry < fields.Datetime.now():
            self.authenticate('tk')

        try:
            resp = requests.post(
                f'{config.api_url}/api/contribution/submit',
                json=employee_data_list,
                headers=self._get_headers(config),
                timeout=60,
            )
            return resp.json()
        except Exception as e:
            _logger.error("BPJS TK submit error: %s", str(e))
            return {'error': str(e)}


class HrBpjsKesConnector(models.Model):
    _name = 'hr.bpjs.kes.connector'
    _description = 'BPJS Kesehatan API Connector'
    _inherit = 'hr.bpjs.api.connector'

    @api.model
    def check_participant(self, no_peserta):
        """Cek kepesertaan BPJS Kesehatan."""
        config = self._get_config('kes')
        if not config.token or config.token_expiry < fields.Datetime.now():
            self.authenticate('kes')

        try:
            resp = requests.get(
                f'{config.api_url}/Peserta/noKartu/{no_peserta}',
                headers=self._get_headers(config),
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            _logger.error("BPJS Kes check error: %s", str(e))
            return {'error': str(e)}

    @api.model
    def submit_contribution(self, employee_data_list):
        """Submit kontribusi BPJS Kesehatan."""
        config = self._get_config('kes')
        if not config.token or config.token_expiry < fields.Datetime.now():
            self.authenticate('kes')

        try:
            resp = requests.post(
                f'{config.api_url}/kontribusi/submit',
                json=employee_data_list,
                headers=self._get_headers(config),
                timeout=60,
            )
            return resp.json()
        except Exception as e:
            _logger.error("BPJS Kes submit error: %s", str(e))
            return {'error': str(e)}
