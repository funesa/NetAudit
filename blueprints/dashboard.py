from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from core.decorators import login_required, ad_required, tickets_required, premium_required
from shared_state import scan_status
from utils import logger, load_general_settings
from concurrent.futures import ThreadPoolExecutor
import os
import time

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/home')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    # Wizard check
    if not session.get('wizard_completed') and session.get('is_master'):
        from app import app_data_dir # Will need to fix this or move app_data_dir to utils
        wizard_file = os.path.join(os.environ.get('APPDATA', ''), 'NetAudit Enterprise', 'wizard_completed.flag')
        if not os.path.exists(wizard_file):
            return redirect(url_for('dashboard.wizard_page'))
    return render_template('dashboard.html')

@dashboard_bp.route('/wizard')
@login_required
def wizard_page():
    if not session.get('is_master'):
        return redirect(url_for('dashboard.dashboard'))
    return render_template('wizard.html')

@dashboard_bp.route('/api/wizard/complete', methods=['POST'])
@login_required
def api_wizard_complete():
    wizard_file = os.path.join(os.environ.get('APPDATA', ''), 'NetAudit Enterprise', 'wizard_completed.flag')
    try:
        os.makedirs(os.path.dirname(wizard_file), exist_ok=True)
        with open(wizard_file, 'w') as f:
            f.write('completed')
        session['wizard_completed'] = True
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

@dashboard_bp.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    try:
        username = session.get('username')
        start_time = time.time()
        
        def fetch_users():
            try:
                from ad_helper import get_all_users
                return get_all_users()
            except: return []

        def fetch_tickets():
            try:
                from glpi_helper import get_my_tickets
                return get_my_tickets(username)
            except: return []

        settings = load_general_settings()
        ad_enabled = settings.get('ad_enabled', True)
        tickets_enabled = settings.get('tickets_enabled', True)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_users = executor.submit(fetch_users) if ad_enabled else None
            future_tickets = executor.submit(fetch_tickets) if tickets_enabled else None
            
            # Recarrega se estiver vazio ou se o último refresh foi há mais de 30s
            last_total = len(scan_status.get("results", []))
            if not scan_status.get("results", []) or (time.time() - scan_status.get("last_refresh", 0) > 30):
                from database import load_all_devices
                scan_status["results"] = load_all_devices()
                scan_status["last_refresh"] = time.time()
                print(f"DEBUG: dashboard_stats - Cache recarregado. Total: {len(scan_status['results'])}")

            os_dist = {}
            type_dist = {}
            online_devices = scan_status.get("results", [])
            print(f"DEBUG: dashboard_stats - total devices: {len(online_devices)}")
            if online_devices:
                print(f"DEBUG: first device status: {online_devices[0].get('status_code')} last_seen: {online_devices[0].get('last_seen')}")
            
            for d in online_devices:
                os_name = d.get('os_detail', 'N/A')
                if 'Windows' in os_name: os_name = 'Windows'
                elif 'Linux' in os_name: os_name = 'Linux'
                elif 'Printer' in os_name or d.get('device_type') == 'printer': os_name = 'Impressoras'
                else: os_name = 'Outros/Rede'
                os_dist[os_name] = os_dist.get(os_name, 0) + 1
                dtype = d.get('device_type', 'network')
                type_dist[dtype] = type_dist.get(dtype, 0) + 1
            
            users = future_users.result(timeout=10) if future_users else []
            tickets = future_tickets.result(timeout=10) or []
        
        # Garantir que são listas
        if not isinstance(users, list): users = []
        if not isinstance(tickets, list): tickets = []

        ticket_stats = {"new": 0, "processing": 0, "solved": 0, "closed": 0}
        for t in tickets:
            if isinstance(t, dict):  # Validar que t é um dicionário
                sid = t.get('status')
                if sid == 1: ticket_stats["new"] += 1
                elif sid in [2, 3, 4]: ticket_stats["processing"] += 1
                elif sid == 5: ticket_stats["solved"] += 1
                elif sid == 6: ticket_stats["closed"] += 1

        global_alerts = 0
        try:
            from ad_helper import get_failed_logins
            fl = get_failed_logins(24)
            global_alerts = len(fl) if fl else 0
        except: pass

        return jsonify({
            'total_users': len(users),
            'active_users': len([u for u in users if u.get('enabled', False)]),
            'os_distribution': os_dist,
            'device_types': type_dist,
            'ticket_stats': ticket_stats,
            'online_count': sum(1 for d in online_devices if d.get("status_code") == "ONLINE"),
            'total_devices': len(online_devices),
            'global_alerts': global_alerts
        })
    except Exception as e:
        logger.error(f"Dashboard Stats Error: {e}")
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/sidebar/alerts')
@login_required
def api_sidebar_alerts():
    try:
        username = session.get('username', 'system')
        alerts = {
            'full_disks': 0, 'offline_servers': 0, 'failed_logins': 0, 'total_alerts': 0, 'new_tickets': 0,
            'failed_logins_severity': 'none', 'disk_warnings': 0, 'disk_warnings_severity': 'none'
        }

        def safe_disks():
            try: from ad_helper import get_disk_alerts; return get_disk_alerts()
            except: return []
        def safe_offline():
            try: from ad_helper import get_offline_servers; return get_offline_servers()
            except: return []
        def safe_logins():
            try: from ad_helper import get_failed_logins; return get_failed_logins()
            except: return []
        def safe_tickets():
            try: from glpi_helper import get_my_tickets; return get_my_tickets(username)
            except: return []

        settings = load_general_settings()
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_disks = executor.submit(safe_disks) if settings.get('ad_enabled') else None
            f_offline = executor.submit(safe_offline) if settings.get('ad_enabled') else None
            f_logins = executor.submit(safe_logins) if settings.get('ad_enabled') else None
            f_tickets = executor.submit(safe_tickets) if settings.get('tickets_enabled') else None

            disk_alerts = f_disks.result(timeout=10) if f_disks else []
            offline_servers = f_offline.result(timeout=10) if f_offline else []
            failed_logins = f_logins.result(timeout=10) if f_logins else []
            tickets = f_tickets.result(timeout=10) if f_tickets else []
        
        # Garantir que são listas
        if not isinstance(disk_alerts, list): disk_alerts = []
        if not isinstance(offline_servers, list): offline_servers = []
        if not isinstance(failed_logins, list): failed_logins = []
        if not isinstance(tickets, list): tickets = []

        alerts['full_disks'] = len(disk_alerts)
        alerts['offline_servers'] = len(offline_servers)
        alerts['failed_logins'] = len(failed_logins)
        alerts['new_tickets'] = sum(1 for t in tickets if isinstance(t, dict) and t.get('status') == 1)
        alerts['total_alerts'] = alerts['full_disks'] + alerts['offline_servers'] + alerts['new_tickets']
        
        if alerts['full_disks'] > 0: alerts['disk_warnings_severity'] = 'critical'
        if alerts['failed_logins'] > 0: alerts['failed_logins_severity'] = 'warning'

        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Sidebar Alerts Error: {e}")
        return jsonify({'error': str(e)}), 500
