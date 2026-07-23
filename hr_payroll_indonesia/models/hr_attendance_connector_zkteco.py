# -*- coding: utf-8 -*-
"""
hr.attendance.connector.zkteco — ZKTeco Direct Connection
===========================================================
Connector untuk ZKTeco devices via TCP/UDP menggunakan pyzk library.
Support: ZKTeco, Fingerspot (ZKTeco-compatible), dan merek sejenis.
"""
import logging
from datetime import datetime

from odoo import models, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

try:
    from zk import ZK, const
    HAS_PYZK = True
except ImportError:
    HAS_PYZK = False
    _logger.warning("pyzk tidak terinstall. Install dengan: pip install pyzk")


class HrAttendanceConnectorZkteco(models.Model):
    _name = 'hr.attendance.connector.zkteco'
    _description = 'ZKTeco Direct Connector'
    _inherit = 'hr.attendance.connector'

    def _get_zk_connection(self, device):
        """Buat koneksi ZK ke device."""
        if not HAS_PYZK:
            raise ValidationError(
                'Library pyzk tidak terinstall.\n'
                'Install dengan: pip install pyzk'
            )

        port = device.port or 4370
        password = int(device.comm_key or 0)
        ip = device.ip_address

        if not ip:
            raise ValidationError('Alamat IP harus diisi!')

        zk = ZK(ip, port=port, timeout=5, password=password,
                 force_udp=False, ommit_ping=False)
        return zk

    def test_connection(self, device):
        """Test koneksi ke ZKTeco device."""
        zk = self._get_zk_connection(device)
        conn = None
        try:
            conn = zk.connect()
            if conn:
                firmware = conn.get_firmware_version() or ''
                serial = conn.get_serialnumber() or ''
                platform = conn.get_platform() or ''
                return {
                    'success': True,
                    'serial_number': serial,
                    'firmware': f"{firmware} ({platform})",
                }
            else:
                return {'success': False, 'error': 'Gagal koneksi ke device'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

    def pull_attendance(self, device, date_from=None, date_to=None):
        """Ambil data attendance dari ZKTeco device."""
        zk = self._get_zk_connection(device)
        conn = None
        try:
            conn = zk.connect()
            if not conn:
                raise ValidationError('Gagal koneksi ke device!')

            # Disable device sambil pull data
            conn.disable_device()

            # Get attendance logs
            attendances = conn.get_attendance()

            # Enable device kembali
            conn.enable_device()

            if not conn:
                conn.disconnect()
                conn = None

            # Process attendance data
            logs_data = []
            for att in attendances:
                # Filter by date if specified
                if date_from and att.timestamp.date() < date_from:
                    continue
                if date_to and att.timestamp.date() > date_to:
                    continue

                # Map punch type: 0=checkin, 1=checkout
                punch_type = '1' if att.status == 1 else '0'

                # Map verify mode
                verify_mode = str(att.punch or 1)

                logs_data.append({
                    'employee_pin': str(att.user_id),
                    'timestamp': att.timestamp,
                    'punch_type': punch_type,
                    'verify_mode': verify_mode,
                    'raw_data': f"user_id={att.user_id}, status={att.status}, "
                               f"punch={att.punch}, work_code={att.work_code}",
                })

            return logs_data

        except Exception as e:
            _logger.error("ZKTeco pull attendance error: %s", str(e))
            raise ValidationError(f"Gagal mengambil data: {str(e)}")
        finally:
            if conn:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except Exception:
                    pass

    def sync_time(self, device):
        """Sinkronisasi waktu device dengan server."""
        zk = self._get_zk_connection(device)
        conn = None
        try:
            conn = zk.connect()
            if not conn:
                raise ValidationError('Gagal koneksi ke device!')

            conn.set_time(datetime.now())
            return True
        except Exception as e:
            raise ValidationError(f"Gagal sinkronisasi waktu: {str(e)}")
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

    def get_users(self, device):
        """Ambil daftar user dari device."""
        zk = self._get_zk_connection(device)
        conn = None
        try:
            conn = zk.connect()
            if not conn:
                raise ValidationError('Gagal koneksi ke device!')

            users = conn.get_users()
            result = []
            for u in users:
                result.append({
                    'uid': u.uid,
                    'user_id': u.user_id,
                    'name': u.name,
                    'privilege': u.privilege,
                })
            return result
        except Exception as e:
            raise ValidationError(f"Gagal mengambil data user: {str(e)}")
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass
