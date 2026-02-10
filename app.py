import os
import sys
import threading
import time
import platform
import webbrowser
from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from flask_session import Session
from dotenv import load_dotenv

# Local Imports
import utils
from utils import logger, resource_path, load_general_settings, migrate_legacy_data
migrate_legacy_data()

from database import init_db, load_all_devices
from shared_state import scan_status
from scanner.scheduler import scheduler_loop, schedule_config
from scanner.engine import rdp_gateway_loop
from security import get_flask_secret_key
import datetime

# Blueprints
from ai_actions import ai_bp
from blueprints.auth import auth_bp
from blueprints.dashboard import dashboard_bp
from blueprints.inventory import inventory_bp
from blueprints.ad_management import ad_bp
from blueprints.helpdesk import helpdesk_bp
from blueprints.monitoring import monitoring_bp
from blueprints.settings_management import settings_bp
from blueprints.license_management import license_bp
from blueprints.alerts import alerts_bp

# Load Env
load_dotenv()

# Global Constants
APP_VERSION = "2.0.0"
ADMIN_USER = os.environ.get("NETAUDIT_SCAN_USER", "")
ADMIN_PASS = os.environ.get("NETAUDIT_SCAN_PASS", "")

# App Setup
if getattr(sys, 'frozen', False):
    app_data_dir = os.path.join(os.environ.get('APPDATA'), 'NetAudit Enterprise')
    os.makedirs(app_data_dir, exist_ok=True)
    os.chdir(app_data_dir)
else:
    app_data_dir = os.getcwd()

app = Flask(__name__, 
            template_folder=resource_path('templates'), 
            static_folder=resource_path('static'))

# CORS Configuration - Restringindo para localhost e IPs locais
from flask_cors import CORS

def get_allowed_origins():
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Tenta descobrir IP local para permitir acesso remoto na rede interna
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        origins.append(f"http://{local_ip}:5173")
    except: pass
    return origins

CORS(app, 
     origins=get_allowed_origins(),
     supports_credentials=True)

# Segurança de Sessão
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET") or get_flask_secret_key()
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=12)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Impede acesso via JS (XSS)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if getattr(sys, 'frozen', False):
    app.config['SESSION_FILE_DIR'] = os.path.join(app_data_dir, 'flask_session')
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

Session(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(ad_bp)
app.register_blueprint(helpdesk_bp)
app.register_blueprint(monitoring_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(license_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(alerts_bp)

# Metrics Blueprint
from api_metrics import metrics_bp
app.register_blueprint(metrics_bp)

@app.route('/api/debug/state')
def debug_state():
    results = scan_status.get("results", [])
    online = sum(1 for d in results if d.get("status_code") == "ONLINE")
    print(f">>> [DEBUG API] Total: {len(results)}, Online: {online}")
    return jsonify({
        "total_results": len(results),
        "online_count": online,
        "first_device": results[0] if results else None
    })

@app.context_processor
def inject_globals():
    from license_manager import lic_manager
    return dict(
        app_version=APP_VERSION,
        is_premium=lic_manager.is_premium(),
        has_pro_access=lic_manager.has_pro_access(),
        trial_days_left=lic_manager.get_trial_status(),
        general_settings=load_general_settings(),
        permissions=session.get('permissions', {})
    )

@app.route('/')
def index():
    from blueprints.auth import check_setup
    if not check_setup():
        return redirect(url_for('auth.setup_page'))
    return render_template('landing.html')

def start_background_services():
    """Initialize all background services (called by launcher.py)"""
    # Initialize DB
    init_db()
    
    # Run migrations
    try:
        from migrate_add_is_active import migrate_add_is_active
        migrate_add_is_active()
    except Exception as e:
        logger.warning(f"Migration error (is_active): {e}")
    
    try:
        from migrate_add_permissions import migrate_add_permissions
        migrate_add_permissions()
    except Exception as e:
        logger.warning(f"Migration error (permissions): {e}")
    
    # Load devices into memory
    scan_status["results"] = load_all_devices()
    logger.info(f"Memória carregada: {len(scan_status['results'])} ativos.")

    # Start background threads
    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=rdp_gateway_loop, daemon=True).start()

    # Start metrics collector
    try:
        from metrics_collector import collector
        logger.info("Aguardando estabilização para iniciar Sentinel...")
        time.sleep(2) 
        collector.start()
        logger.info("Monitoring active!")
    except Exception as e:
        logger.warning(f"Collector error: {e}")

if __name__ == '__main__':
    # Initialize DB
    init_db()
    
    # Run migrations
    try:
        from migrate_add_is_active import migrate_add_is_active
        migrate_add_is_active()
    except Exception as e:
        print(f"[WARN] Migration error (is_active): {e}")
        
    try:
        from migrate_add_permissions import migrate_add_permissions
        migrate_add_permissions()
    except Exception as e:
        print(f"[WARN] Migration error (permissions): {e}")
    
    scan_status["results"] = load_all_devices()
    print(f"[SYSTEM] Memória carregada: {len(scan_status['results'])} ativos.")

    # Background Services
    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=rdp_gateway_loop, daemon=True).start()

    # Metrics Collector
    try:
        from metrics_collector import collector
        print("[SYSTEM] Aguardando estabilização para iniciar Sentinel...")
        time.sleep(2) 
        collector.start()
        print("[INFO] Monitoring active!")
    except Exception as e:
        print(f"[WARN] Collector error: {e}")

    # Browser management
    if getattr(sys, 'frozen', False):
        threading.Thread(target=lambda: (time.sleep(2), webbrowser.open('http://127.0.0.1:5000')), daemon=True).start()

    # Serve
    if getattr(sys, 'frozen', False):
        try:
            from waitress import serve
            serve(app, host='0.0.0.0', port=5000, threads=12)
        except:
            app.run(host='0.0.0.0', port=5000)
    else:
        app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
