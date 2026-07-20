# -*- coding: utf-8 -*-
"""
Flask ADMS Configuration
=========================
Konfigurasi untuk Flask ADMS server yang menerima data push dari ZKTeco devices.
"""
import os


class Config:
    """Base configuration."""
    # Flask
    SECRET_KEY = os.environ.get('ADMS_SECRET_KEY', 'hr-payroll-adms-secret-key-change-in-production')

    # Odoo connection
    ODOO_URL = os.environ.get('ODOO_URL', 'http://localhost:8069')
    ODOO_DB = os.environ.get('ODOO_DB', 'odoo')
    ODOO_USER = os.environ.get('ODOO_USER', 'admin')
    ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'admin')

    # ADMS Server
    ADMS_PORT = int(os.environ.get('ADMS_PORT', 8068))
    ADMS_HOST = os.environ.get('ADMS_HOST', '0.0.0.0')

    # Authentication — API key for device/server communication
    # Set ADMS_API_KEY env var to enable authentication
    # If empty, authentication is disabled (not recommended for production)
    ADMS_API_KEY = os.environ.get('ADMS_API_KEY', '')

    # Device communication key (must match device settings)
    DEFAULT_COMM_KEY = os.environ.get('ADMS_COMM_KEY', '')

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
