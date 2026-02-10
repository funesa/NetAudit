from flask import Blueprint, render_template, request, jsonify, session
from core.decorators import login_required
from core.permissions import require_permission
from scanner.engine import scan_thread, get_full_audit, save_db
from shared_state import scan_status, scan_lock, results_lock, update_scan_status
from ip_manager import get_ip_map, get_free_ips, suggest_next_ip
from utils import logger, validate_subnet, rate_limiter, api_error_handler, load_general_settings
import threading
import time
import subprocess
import platform

# Windows specific
CREATE_NO_WINDOW = 0x08000000 if platform.system() == 'Windows' else 0

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/scan')
@login_required
@require_permission('view_all')
def scan_page():
    return render_template('scanner.html')

@inventory_bp.route('/api/scanner/start', methods=['POST'])
@login_required
@require_permission('run_scan')
@api_error_handler
def run_scan():
    username = session.get('username', 'unknown')
    if not rate_limiter.is_allowed(f"scan_{username}"):
        return jsonify({"success": False, "error": "rate_limit", "message": "Muitas requisições."}), 429
    
    if scan_status["running"]:
        return jsonify({"success": False, "error": "already_running", "message": "Scan já está em execução"}), 409
    
    data = request.json
    subnet = data.get('subnet')
    if not subnet:
        raise ValueError("Subnet não fornecida")
    
    # Sanitizar input antes de usar
    subnet = subnet.replace(';', '/').replace(':', '/')
    
    valid, error_msg = validate_subnet(subnet)
    if not valid:
        raise ValueError(error_msg)
    
    logger.info(f"Iniciando comando de scan Sentinel para: {subnet}")
    
    # Resetar estado global de forma atômica
    update_scan_status({
        "running": True,
        # "results": [],  <-- REMOVED to persist inventory
        "scanned": 0,
        "total": 510 if '/23' in subnet else 254,
        "logs": [{"msg": f"Sentinel Engine: Preparando varredura em {subnet}...", "time": time.strftime("%H:%M:%S")}],
        "etr": "Iniciando...",
        "last_results": {"updated": 0, "added": 0, "total_found": 0}
    })

    # Get credentials
    settings = load_general_settings()
    ad_config = settings.get('ad_config', {})
    import os
    admin_user = ad_config.get('username') or os.environ.get("NETAUDIT_SCAN_USER", "")
    admin_pass = ad_config.get('password') or os.environ.get("NETAUDIT_SCAN_PASS", "")

    t = threading.Thread(target=scan_thread, args=(subnet, admin_user, admin_pass), daemon=True)
    t.start()
    
    return jsonify({"success": True, "message": "Sentinel Core: Processo disparado", "subnet": subnet})

@inventory_bp.route('/api/scanner/stop', methods=['POST'])
@login_required
@require_permission('run_scan')
def stop_scan():
    scan_status["running"] = False
    return jsonify({"success": True, "message": "Parada solicitada"})

@inventory_bp.route('/api/scanner/status')
@login_required
@require_permission('view_all')
def status():
    p = 0
    with scan_lock:
        if scan_status.get("total", 0) > 0:
            # Evita divisão por zero e caps em 100
            p = int((scan_status.get("scanned", 0) / scan_status["total"]) * 100)
            if p > 100: p = 100
    
    return jsonify({
        "running": scan_status["running"],
        # Frontend usa status para barra de progresso, results vem em outra chamada mas podemos mandar aqui também se quiser
        "progress": p,
        "total": scan_status["total"],
        "scanned": scan_status["scanned"],
        "scanned_ips": scan_status["scanned"],
        "total_ips": scan_status["total"],
        "etr": scan_status["etr"],
        "last_results": scan_status.get("last_results", {"updated": 0, "added": 0, "total_found": 0}),
        "logs": scan_status.get("logs", [])
    })

@inventory_bp.route('/api/scanner/results')
@login_required
@require_permission('view_all')
def scanner_results():
    # Retorna apenas a lista de dispositivos para a tabela
    return jsonify(scan_status["results"])

@inventory_bp.route('/ip-map')
@login_required
def ip_map_page():
    return render_template('ip_map.html')

@inventory_bp.route('/api/ip-map')
@login_required
def api_ip_map():
    subnet = request.args.get('subnet')
    days = request.args.get('days', 7, type=int)
    return jsonify(get_ip_map(subnet, days))

@inventory_bp.route('/api/ip-map/free')
@login_required
def api_free_ips():
    subnet = request.args.get('subnet')
    days = request.args.get('days', 7, type=int)
    return jsonify(get_free_ips(subnet, days))

@inventory_bp.route('/api/ip-map/suggest')
@login_required
def api_suggest_ip():
    subnet = request.args.get('subnet')
    days = request.args.get('days', 7, type=int)
    if not subnet:
        from ip_manager import get_active_subnet
        subnet = get_active_subnet()
    
    if not subnet:
        return jsonify({'error': 'Nenhuma subnet identificada.'})
        
    return jsonify(suggest_next_ip(subnet, days))

@inventory_bp.route('/api/scan/individual', methods=['POST'])
@login_required
@require_permission('run_scan')
def api_scan_individual():
    data = request.json
    ip = data.get('ip')
    if not ip: return jsonify({"error": "IP missing"}), 400
    
    settings = load_general_settings()
    ad_config = settings.get('ad_config', {})
    import os
    admin_user = ad_config.get('username') or os.environ.get("NETAUDIT_SCAN_USER", "")
    admin_pass = ad_config.get('password') or os.environ.get("NETAUDIT_SCAN_PASS", "")

    res = get_full_audit(ip, admin_user, admin_pass)
    if res:
        with results_lock:
            found = False
            for i, existing in enumerate(scan_status["results"]):
                if existing['ip'] == ip:
                    scan_status["results"][i] = res
                    found = True
                    break
            if not found:
                scan_status["results"].append(res)
            save_db(scan_status["results"])
        return jsonify({"success": True, "data": res})
    
    return jsonify({"success": False, "message": "Offline"})

@inventory_bp.route('/api/scanner/diagnostics/ping', methods=['POST'])
@login_required
def api_ping_test():
    ip = request.json.get('ip')
    if not ip: return jsonify({"error": "IP missing"}), 400
    
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    try:
        test_count = '5'
        cmd = ['ping', param, test_count, ip]
        
        # 5 pings can take up to 20s (4s timeout * 5) on Windows if host is down
        # Set timeout to 25s to be safe
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW, timeout=25)
        
        if proc.returncode == 0:
            return jsonify({"success": True, "output": proc.stdout})
        else:
            return jsonify({"success": True, "output": proc.stdout or proc.stderr or "Ping falhou (Host inacessível)"})
            
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "message": f"Timeout: O teste de ping demorou muito para responder (>{25}s). O dispositivo pode estar offline ou bloqueando ICMP."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno ao executar ping: {str(e)}"})
