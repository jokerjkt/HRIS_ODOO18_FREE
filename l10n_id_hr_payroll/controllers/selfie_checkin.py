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

_logger = logging.getLogger(__name__)


class SelfieCheckInController(http.Controller):

    @http.route('/l10n_id_hr_payroll/selfie_checkin', type='json',
                auth='user', methods=['POST'], csrf=True)
    def selfie_checkin(self, **kwargs):
        """
        Handle selfie check-in/check-out from the OWL component.

        Expected JSON params:
          - employee_pin: str
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

        # Find geo-fence zone
        zone = request.env['hr.attendance.geo.fence'].find_zone_for_point(
            latitude, longitude, employee
        )
        zone_name = zone.name if zone else 'Outside all zones'
        inside_fence = bool(zone)

        # Process photo
        photo_b64_encoded = False
        if photo_b64:
            try:
                photo_bytes = base64.b64decode(photo_b64)
                photo_b64_encoded = base64.b64encode(photo_bytes).decode('utf-8')
            except Exception:
                photo_b64_encoded = False

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
            if photo_b64_encoded:
                att_vals['check_in_photo'] = photo_b64_encoded

            if attendance:
                attendance.write(att_vals)
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
            if photo_b64_encoded:
                att_vals['check_out_photo'] = photo_b64_encoded

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
