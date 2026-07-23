# -*- coding: utf-8 -*-
"""
Selfie Check-In Controller — Mobile PWA Attendance
====================================================
Handles the OWL component's RPC calls for selfie-based attendance.
"""
import base64
import logging
from datetime import datetime

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class SelfieCheckInController(http.Controller):

    @http.route('/hr_payroll_indonesia/selfie_checkin', type='json',
                auth='user', methods=['POST'])
    def selfie_checkin(self, **kwargs):
        """
        Handle selfie check-in/check-out from the OWL component.

        Expected JSON params:
          - latitude: float
          - longitude: float
          - accuracy: float (GPS accuracy in meters)
          - photo: str (base64-encoded JPEG image)
          - device_type: str ('mobile')
          - device_info: str (user agent)
        """
        data = request.jsonrequest

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy', 0)
        photo_b64 = data.get('photo', '')
        device_type = data.get('device_type', 'mobile')
        device_info = data.get('device_info', '')

        # Validate required fields
        if latitude is None or longitude is None:
            return {'success': False, 'error': 'Lokasi GPS wajib diaktifkan'}

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            accuracy = float(accuracy) if accuracy else 0
        except (ValueError, TypeError):
            return {'success': False, 'error': 'Format GPS tidak valid'}

        # Find employee from logged-in user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.uid),
            ('active', '=', True),
        ], limit=1)

        if not employee:
            return {'success': False, 'error': 'Akun Anda tidak terkait dengan karyawan manapun'}

        try:
            return self._process_attendance(
                employee, latitude, longitude, accuracy,
                photo_b64, device_type, device_info,
            )
        except AccessError as e:
            _logger.error("Access error during selfie checkin: %s", e)
            return {'success': False, 'error': 'Tidak memiliki akses untuk operasi ini'}
        except UserError as e:
            _logger.warning("User error during selfie checkin: %s", e)
            return {'success': False, 'error': str(e)}
        except Exception as e:
            _logger.exception("Unexpected error during selfie checkin for employee %s", employee.name)
            return {'success': False, 'error': 'Terjadi kesalahan sistem. Silakan coba lagi.'}

    def _process_attendance(self, employee, latitude, longitude, accuracy,
                            photo_b64, device_type, device_info):
        """Core attendance processing logic."""
        # Find geo-fence zone
        zone = request.env['hr.attendance.geo.fence'].sudo().find_zone_for_point(
            latitude, longitude, employee
        )
        zone_name = zone.name if zone else 'Outside all zones'
        inside_fence = bool(zone)

        # Process photo — store base64 directly (no unnecessary re-encode)
        photo_data = False
        if photo_b64:
            try:
                # Validate that it's valid base64
                photo_bytes = base64.b64decode(photo_b64, validate=True)
                if len(photo_bytes) > 5 * 1024 * 1024:  # 5MB limit
                    return {'success': False, 'error': 'Ukuran foto maksimal 5MB'}
                photo_data = base64.b64encode(photo_bytes).decode('utf-8')
            except Exception:
                _logger.warning("Invalid photo data received from employee %s", employee.name)
                photo_data = False

        # Determine check-in or check-out (toggle based on today's attendance)
        today = fields.Date.context_today(request.env.user)
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        existing = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', today_start),
            ('check_in', '<=', today_end),
        ], order='check_in desc', limit=1)

        # Toggle: if exists and no check_out, this is check-out; otherwise check-in
        action = 'check_in'
        attendance = False

        if existing and not existing.check_out:
            action = 'check_out'
            attendance = existing

        now = fields.Datetime.now()

        if action == 'check_in':
            att_vals = {
                'employee_id': employee.id,
                'check_in': now,
                'check_in_latitude': latitude,
                'check_in_longitude': longitude,
                'check_in_accuracy': accuracy,
                'device_type': device_type,
                'check_in_device_info': device_info,
            }
            if photo_data:
                att_vals['check_in_photo'] = photo_data

            if attendance:
                attendance.sudo().write(att_vals)
            else:
                attendance = request.env['hr.attendance'].sudo().create(att_vals)
        else:
            att_vals = {
                'check_out': now,
                'check_out_latitude': latitude,
                'check_out_longitude': longitude,
                'check_out_accuracy': accuracy,
                'check_out_device_info': device_info,
            }
            if photo_data:
                att_vals['check_out_photo'] = photo_data

            attendance.sudo().write(att_vals)

        _logger.info(
            "Selfie %s: employee=%s lat=%s lng=%s zone=%s accuracy=%s",
            action, employee.name, latitude, longitude, zone_name, accuracy,
        )

        return {
            'success': True,
            'employee': employee.name,
            'action': action,
            'zone': zone_name,
            'inside_fence': inside_fence,
            'attendance_id': attendance.id if attendance else False,
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
        }
