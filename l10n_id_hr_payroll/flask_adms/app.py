# -*- coding: utf-8 -*-
"""
Flask ADMS Server — ZKTeco Cloud Push Receiver
================================================
Standalone Flask server yang menerima data push dari ZKTeco devices
menggunakan protokol ADMS (Automatic Data Master Server) / iClock.

Endpoints:
  GET/POST /iclock/cdata      — Attendance logs, user data, device info
  GET/POST /iclock/registry   — Device registration
  GET      /iclock/getrequest — Command queue polling
  GET      /iclock/inspect    — JSON status of all connected devices

Usage:
  python -m flask_adms.app
  # atau
  FLASK_APP=flask_adms.app flask run --host=0.0.0.0 --port=8068

Device Configuration (di mesin ZKTeco):
  COMM > Cloud Server Setting:
    Server Address: <your-odoo-ip>
    Server Port: 8068
    Enable: Yes
"""
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

from flask import Flask, request, Response

from .config import config_map

# ─── Logging Setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [ADMS] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('adms')

# ─── Flask App ──────────────────────────────────────────────────────────────
app = Flask(__name__)

# In-memory storage for connected devices and pending commands
# In production, use Redis or database
connected_devices = {}   # SN -> {last_seen, ip, info}
device_logs_buffer = {}  # SN -> [logs]
pending_commands = {}    # SN -> [commands]


def get_config():
    """Get configuration based on environment."""
    env = app.config.get('ENV', 'development')
    return config_map.get(env, config_map['development'])


# ─── Authentication ─────────────────────────────────────────────────────────

def verify_api_key():
    """
    Verify API key from request header or query parameter.
    Returns True if valid or if auth is disabled (empty key).
    Returns False if key is invalid.
    """
    config = get_config()
    api_key = config.ADMS_API_KEY

    # If no API key configured, skip authentication (dev mode)
    if not api_key:
        return True

    # Check X-API-Key header first, then ?api_key= query param
    provided_key = request.headers.get('X-API-Key', '') or request.args.get('api_key', '')

    if provided_key == api_key:
        return True

    logger.warning(
        "Authentication failed: IP=%s key_provided=%s",
        request.remote_addr,
        bool(provided_key),
    )
    return False


# ─── Database Helper ────────────────────────────────────────────────────────

def save_attendance_log(serial_number, user_id, timestamp, status, verify_mode=1, work_code=0):
    """
    Simpan log absensi ke Odoo database via XML-RPC.

    Args:
        serial_number: Serial number device
        user_id: User ID/PIN dari mesin
        timestamp: Waktu absensi (datetime)
        status: 0=Check In, 1=Check Out, 2=Break Out, 3=Break In
        verify_mode: 0=Password, 1=FP, 2=Card, 3=Face
        work_code: Work code (optional)
    """
    config = get_config()

    try:
        import xmlrpc.client
        import socket

        # Koneksi ke Odoo
        sock = xmlrpc.client.ServerProxy(
            f'{config.ODOO_URL}/xmlrpc/2/object',
            allow_none=True,
            use_datetime=True,
        )

        # Authenticate
        uid = sock.execute(
            config.ODOO_DB,
            config.ODOO_USER,
            config.ODOO_PASSWORD,
            'authenticate',
            config.ODOO_DB,
            config.ODOO_USER,
            config.ODOO_PASSWORD,
            {},
        )

        if not uid:
            logger.error("Autentikasi Odoo gagal!")
            return False

        # Cari device berdasarkan serial number
        device_ids = sock.execute(
            config.ODOO_DB, uid, config.ODOO_PASSWORD,
            'hr.attendance.device', 'search_read',
            [('serial_number', '=', serial_number)],
            ['id', 'employee_mapping'],
            0, 1,
        )

        device_id = False
        employee_mapping = 'pin'
        if device_ids:
            device_id = device_ids[0]['id']
            employee_mapping = device_ids[0].get('employee_mapping', 'pin')

        # Cari employee berdasarkan mapping
        employee_id = False
        if employee_mapping == 'pin':
            emp_ids = sock.execute(
                config.ODOO_DB, uid, config.ODOO_PASSWORD,
                'hr.employee', 'search_read',
                [('pin', '=', str(user_id)), ('active', '=', True)],
                ['id'],
                0, 1,
            )
        else:
            emp_ids = sock.execute(
                config.ODOO_DB, uid, config.ODOO_PASSWORD,
                'hr.employee', 'search_read',
                [('identification_id', '=', str(user_id)), ('active', '=', True)],
                ['id'],
                0, 1,
            )

        if emp_ids:
            employee_id = emp_ids[0]['id']

        # Buat device log
        punch_type = '0' if status in (0, '0') else '1'
        verify_str = str(verify_mode)

        log_vals = {
            'device_id': device_id,
            'employee_id': employee_id,
            'employee_pin': str(user_id),
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp),
            'punch_type': punch_type,
            'verify_mode': verify_str,
            'raw_data': f"SN={serial_number} UserID={user_id} Status={status} Verify={verify_mode}",
            'state': 'matched' if employee_id else 'pending',
        }

        log_id = sock.execute(
            config.ODOO_DB, uid, config.ODOO_PASSWORD,
            'hr.attendance.device.log', 'create',
            log_vals,
        )

        logger.info(
            "Log tersimpan: SN=%s UserID=%s Status=%s DeviceID=%s EmployeeID=%s LogID=%s",
            serial_number, user_id, status, device_id, employee_id, log_id,
        )

        # Update last_sync device
        if device_id:
            sock.execute(
                config.ODOO_DB, uid, config.ODOO_PASSWORD,
                'hr.attendance.device', 'write',
                [device_id],
                {'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            )

        return True

    except Exception as e:
        logger.error("Error save_attendance_log: %s", str(e))
        return False


def update_device_status(serial_number, ip_address, info=None):
    """Update status device yang terhubung."""
    connected_devices[serial_number] = {
        'last_seen': datetime.now().isoformat(),
        'ip': ip_address,
        'info': info or {},
    }


# ─── Routes ─────────────────────────────────────────────────────────────────

@app.route('/iclock/cdata', methods=['GET', 'POST'])
def iclock_cdata():
    """
    Endpoint utama untuk menerima data dari ZKTeco devices.

    GET: Device初次 koneksi, register, minta stamp
    POST: Kirim attendance logs, user info, dll

    Parameters:
      SN: Serial number device
      table: ATTLOG, USERINFO, OPERLOG
      Stamp: Timestamp untuk sync
      options: all, fp, face, card, user
    """
    if not verify_api_key():
        return Response("Unauthorized", status=401, mimetype='text/plain')

    sn = request.args.get('SN', '')
    table = request.args.get('table', '')
    stamp = request.args.get('Stamp', '')
    options = request.args.get('options', '')

    client_ip = request.remote_addr

    logger.info(
        "cdata: SN=%s table=%s Stamp=%s options=%s IP=%s method=%s",
        sn, table, stamp, options, client_ip, request.method,
    )

    # Update device status
    update_device_status(sn, client_ip, {
        'table': table,
        'stamp': stamp,
        'options': options,
    })

    if request.method == 'GET':
        # GET request — device polling, return stamp
        return Response(
            f"ATTStamp={stamp or 'None'}\n"
            f"OPERLOGStamp={stamp or 'None'}\n",
            mimetype='text/plain',
            headers={'Content-Type': 'text/plain; charset=utf-8'},
        )

    # POST request — device pushing data
    if table.upper() == 'ATTLOG':
        return _process_attlog(sn, request)

    elif table.upper() == 'USERINFO':
        return _process_userinfo(sn, request)

    elif table.upper() == 'OPERLOG':
        # Operation log — just acknowledge
        logger.info("OPERLOG from SN=%s: %s", sn, request.data[:500] if request.data else '')
        return Response("OK", mimetype='text/plain')

    else:
        logger.warning("Unknown table '%s' from SN=%s", table, sn)
        return Response("OK", mimetype='text/plain')


@app.route('/iclock/registry', methods=['GET', 'POST'])
def iclock_registry():
    """
    Device registration endpoint.

    Devices register themselves with the server and report capabilities.
    """
    sn = request.args.get('SN', '')
    client_ip = request.remote_addr

    if not verify_api_key():
        return Response("Unauthorized", status=401, mimetype='text/plain')

    logger.info("registry: SN=%s IP=%s method=%s", sn, client_ip, request.method)

    if request.method == 'POST':
        # Device registering with additional info
        body = request.data.decode('utf-8', errors='ignore')
        logger.info("Registry body: %s", body[:500])

    update_device_status(sn, client_ip, {'type': 'registry'})

    return Response(
        "SN=" + sn + "\nVER=2.2.14\n",
        mimetype='text/plain',
    )


@app.route('/iclock/getrequest', methods=['GET'])
def iclock_getrequest():
    """
    Device polling for pending commands.

    Returns commands queued by the server (CHECK, RESTART, etc).
    """
    sn = request.args.get('SN', '')
    logger.info("getrequest: SN=%s", sn)

    if not verify_api_key():
        return Response("Unauthorized", status=401, mimetype='text/plain')

    # Check for pending commands
    commands = pending_commands.get(sn, [])

    if commands:
        cmd = commands.pop(0)
        logger.info("Sending command to SN=%s: %s", sn, cmd)
        return Response(cmd, mimetype='text/plain')

    # No pending commands — return empty
    return Response("", mimetype='text/plain')


@app.route('/iclock/devicecmd', methods=['POST'])
def iclock_devicecmd():
    """
    Device reporting command execution results.
    """
    if not verify_api_key():
        return Response("Unauthorized", status=401, mimetype='text/plain')
    sn = request.args.get('SN', '')
    body = request.data.decode('utf-8', errors='ignore')
    logger.info("devicecmd: SN=%s result=%s", sn, body[:500])
    return Response("OK", mimetype='text/plain')


@app.route('/iclock/inspect', methods=['GET'])
def iclock_inspect():
    """
    JSON status of all connected devices.
    Useful for monitoring dashboard.
    """
    if not verify_api_key():
        return Response("Unauthorized", status=401, mimetype='text/plain')
    return Response(
        json.dumps(connected_devices, indent=2),
        mimetype='application/json',
    )


# ─── Helper Functions ───────────────────────────────────────────────────────

def _process_attlog(sn, req):
    """Process ATTLOG data from device."""
    try:
        body = req.data.decode('utf-8', errors='ignore')
        logger.info("ATTLOG from SN=%s: %s", sn, body[:1000])

        # Parse tab-separated attendance data
        lines = body.strip().split('\n')
        saved_count = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse fields: UserID\tTimestamp\tStatus\tVerifyMode\tWorkCode
            parts = line.split('\t')
            if len(parts) < 3:
                continue

            user_id = parts[0].strip()
            timestamp_str = parts[1].strip()
            status = parts[2].strip()
            verify_mode = parts[3].strip() if len(parts) > 3 else '1'
            work_code = parts[4].strip() if len(parts) > 4 else '0'

            # Parse timestamp
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S')
                except ValueError:
                    logger.warning("Cannot parse timestamp: %s", timestamp_str)
                    continue

            # Save to database
            if save_attendance_log(sn, user_id, timestamp, status, verify_mode, work_code):
                saved_count += 1

        logger.info("Processed %d ATTLOG entries from SN=%s", saved_count, sn)
        return Response("OK", mimetype='text/plain')

    except Exception as e:
        logger.error("Error processing ATTLOG: %s", str(e))
        return Response("OK", mimetype='text/plain')


def _process_userinfo(sn, req):
    """Process USERINFO data from device."""
    try:
        body = req.data.decode('utf-8', errors='ignore')
        logger.info("USERINFO from SN=%s: %s", sn, body[:1000])
        # USERINFO sync — just acknowledge for now
        return Response("OK", mimetype='text/plain')
    except Exception as e:
        logger.error("Error processing USERINFO: %s", str(e))
        return Response("OK", mimetype='text/plain')


# ─── CLI Entry Point ────────────────────────────────────────────────────────

def main():
    """Start the ADMS server."""
    config = get_config()
    app.config.from_object(config)

    logger.info("=" * 60)
    logger.info("ADMS Server Starting")
    logger.info("  Host: %s", config.ADMS_HOST)
    logger.info("  Port: %s", config.ADMS_PORT)
    logger.info("  Odoo URL: %s", config.ODOO_URL)
    logger.info("  Odoo DB: %s", config.ODOO_DB)
    logger.info("=" * 60)

    app.run(
        host=config.ADMS_HOST,
        port=config.ADMS_PORT,
        debug=config.DEBUG,
    )


if __name__ == '__main__':
    main()
