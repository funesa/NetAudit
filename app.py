import ipaddress
import socket
import sys
import subprocess
import threading
import time
import platform

# Prevenir abertura de janelas em subprocessos no Windows
CREATE_NO_WINDOW = 0x08000000 if platform.system() == 'Windows' else 0
import json
import os
import re
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session
import webbrowser
from ad_helper import authenticate_ad, get_ad_users, reset_ad_password, login_required, \
    unlock_user_account, toggle_user_status, update_ad_attributes, get_all_ad_groups, manage_group_membership, get_ad_storage, get_failed_logins
from snmp_helper import get_printer_data
from ip_manager import get_ip_map, get_free_ips, suggest_next_ip
from license_manager import lic_manager
from cache_helper import clear_cache
from glpi_helper import SESSION_CACHE, TICKETS_CACHE
from functools import wraps

# Importar utilitários de estabilidade
from utils import (
    logger, validate_ip, validate_subnet, validate_username, validate_password,
    validate_days_threshold, api_error_handler, safe_json_load, safe_json_save,
    retry_on_failure, rate_limiter, load_general_settings, save_general_settings,
    resource_path
)

# Configuração para Compiladores (PyInstaller / cx_Freeze)
if getattr(sys, 'frozen', False):
    # ATENÇÃO: Dados graváveis (DB, Logs, Sessão) DEVEM ir para AppData
    app_data_dir = os.path.join(os.environ.get('APPDATA'), 'NetAudit Enterprise')
    os.makedirs(app_data_dir, exist_ok=True)
    os.chdir(app_data_dir)
else:
    app_data_dir = os.getcwd()

template_folder = resource_path('templates')
static_folder = resource_path('static')
app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

# AI Blueprint
from ai_actions import ai_bp
app.register_blueprint(ai_bp)

# --- VERSÃO DO SISTEMA ---
APP_VERSION = "2026.1.3"

@app.context_processor
def inject_version():
    return dict(app_version=APP_VERSION)

# --- CONFIGURAÇÕES ---
# Lógica para persistência de dados fora do EXE
# Lógica de diretório removida em favor da configuração acima (AppData)

DB_FILE = "scan_history.json"
SCHEDULE_FILE = "scan_schedule.json"
USERS_FILE = "users.json"
LICENSE_FILE = "license.json"
GLPI_CONFIG_FILE = "glpi_config.json"

# Proteção de Credenciais via Variáveis de Ambiente (Hardening)
from dotenv import load_dotenv
load_dotenv()

ADMIN_USER = os.environ.get("NETAUDIT_SCAN_USER", "")
ADMIN_PASS = os.environ.get("NETAUDIT_SCAN_PASS", "")
LICENSE_KEY = os.environ.get("NETAUDIT_LICENSE", "TRIAL-2026-COMMERCIAL")

def create_desktop_shortcut():
    """Cria um atalho na área de trabalho se estiver rodando como EXE"""
    if not getattr(sys, 'frozen', False): return
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "NetAudit Enterprise.lnk")
        target = sys.executable
        
        if not os.path.exists(path):
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = os.path.dirname(target)
            shortcut.IconLocation = target
            shortcut.save()
            print(f"[OK] Atalho criado em: {path}")
    except Exception as e:
        # Fallback simples via PowerShell se as bibliotecas falharem
        try:
            target = sys.executable
            name = "NetAudit Enterprise.lnk"
            cmd = f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), '{name}'));$s.TargetPath='{target}';$s.WorkingDirectory='{os.path.dirname(target)}';$s.Save()"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, creationflags=CREATE_NO_WINDOW)
        except:
            pass

def load_schedule():
    """Carrega configuração de schedule de forma segura"""
    default_config = {
        "enabled": False,
        "interval": 60,
        "unit": "minutes",
        "last_run": None,
        "subnet": ""
    }
    return safe_json_load(SCHEDULE_FILE, default=default_config)

def save_schedule(config):
    """Salva configuração de schedule de forma segura"""
    return safe_json_save(SCHEDULE_FILE, config)

schedule_config = load_schedule()

def premium_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow Premium OR Valid Trial
        if not lic_manager.has_pro_access():
            return redirect(url_for('license_page'))
        return f(*args, **kwargs)
    return decorated_function

def check_setup():
    """Verifica se o sistema já foi configurado (primeiro usuário)"""
    users = safe_json_load("users.json", default=[])
    return len(users) > 0

def get_master_user():
    """Retorna o nome do usuário master (primeiro criado)"""
    users = safe_json_load("users.json", default=[])
    for u in users:
        if u.get('is_master'):
            return u.get('username')
    # Fallback para o primeiro da lista se is_master não existir (migração)
    return users[0].get('username') if users else None

# Session Configuration
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET", "netaudit-default-secret-2026")
app.config['SESSION_TYPE'] = 'filesystem'
# FORÇAR caminho da sessão para AppData para evitar erro de permissão
if getattr(sys, 'frozen', False):
    app.config['SESSION_FILE_DIR'] = os.path.join(os.environ.get('APPDATA'), 'NetAudit Enterprise', 'flask_session')
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
Session(app)

def ad_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        settings = load_general_settings()
        user_perms = session.get('permissions', {})
        
        # Acesso PRO Requerido
        if not lic_manager.has_pro_access():
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso ao AD requer licença Premium ou Trial ativo.', 'results': []}), 403
            return redirect(url_for('license_page'))

        # Verifica se o AD está habilitado globalmente E para o usuário
        if not settings.get('ad_enabled', True) or not user_perms.get('ad', True):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso ao AD não permitido ou desativado.', 'count': 0, 'results': [], 'os_distribution': {}, 'device_types': {}, 'ticket_stats': {}}), 200
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso negado. Requer privilégios de administrador.'}), 403
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def tickets_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        settings = load_general_settings()
        user_perms = session.get('permissions', {})
        
        # Acesso PRO Requerido
        if not lic_manager.has_pro_access():
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso ao Helpdesk requer licença Premium ou Trial ativo.', 'tickets': []}), 403
            return redirect(url_for('license_page'))

        # Verifica se o Helpdesk está habilitado globalmente E para o usuário
        if not settings.get('tickets_enabled', True) or not user_perms.get('helpdesk', True):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso ao Helpdesk não permitido ou desativado.', 'count': 0, 'results': [], 'ticket_stats': {}}), 200
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# General Settings Management (Movido para utils.py)


@app.context_processor
def inject_globals():
    return dict(
        is_premium=lic_manager.is_premium(),
        has_pro_access=lic_manager.has_pro_access(),
        trial_days_left=lic_manager.get_trial_status(),
        general_settings=load_general_settings()
    )

@app.route('/api/settings/general', methods=['GET', 'POST'])
@login_required
def general_settings_route():
    if request.method == 'POST':
        data = request.json
        current = load_general_settings()
        
        # Update allowed keys
        if 'ai_enabled' in data:
            current['ai_enabled'] = bool(data['ai_enabled'])
        if 'ad_enabled' in data:
            val = bool(data['ad_enabled'])
            if current.get('ad_enabled') and not val:
                # Desativando: Limpar configurações e DADOS
                logger.info("### DESATIVANDO AD: Iniciando limpeza profunda...")
                for f in ['ad_config.json', 'ad_last_connection.json', 'ad_cache.json']:
                    abs_path = os.path.join(os.getcwd(), f)
                    if os.path.exists(abs_path):
                        try:
                            os.remove(abs_path)
                            logger.info(f"Removido: {f}")
                        except Exception as e:
                            logger.error(f"Erro ao remover {f}: {e}")
                
                # Limpar cache em memória
                clear_cache()
            current['ad_enabled'] = val
        if 'tickets_enabled' in data:
            val = bool(data['tickets_enabled'])
            if current.get('tickets_enabled') and not val:
                # Desativando: Limpar GLPI config e cache
                logger.info("### DESATIVANDO HELPDESK: Iniciando limpeza profunda...")
                abs_path = os.path.join(os.getcwd(), 'glpi_config.json')
                if os.path.exists(abs_path):
                    try:
                        os.remove(abs_path)
                        logger.info("Removido: glpi_config.json")
                    except Exception as e:
                        logger.error(f"Erro ao remover glpi_config.json: {e}")
                
                # Limpar cache em memória
                SESSION_CACHE.clear()
                TICKETS_CACHE.clear()
            current['tickets_enabled'] = val
        if 'dashboard_refresh_interval' in data:
            try:
                current['dashboard_refresh_interval'] = int(data['dashboard_refresh_interval'])
            except:
                pass
        
        save_general_settings(current)
        return jsonify({"status": "success", "settings": current})
    
    return jsonify(load_general_settings())


# Active Directory Configuration (já está em ad_helper.py)


def load_db():
    """Carrega histórico de scans de forma segura"""
    data = safe_json_load(DB_FILE, default=[])
    
    # Garantir que é sempre uma lista
    if isinstance(data, dict):
        logger.warning("Convertendo formato antigo de dict para list")
        return list(data.values())
    
    return data if isinstance(data, list) else []

def save_db(data):
    """Salva histórico de scans de forma segura com backup"""
    if not isinstance(data, list):
        logger.error(f"Tentativa de salvar dados inválidos: {type(data)}")
        return False
    
    return safe_json_save(DB_FILE, data)

# --- INTELIGÊNCIA DO DISPOSITIVO ---
mac_vendor_cache = {}

class DeviceIntelligence:
    @staticmethod
    def get_mac_address(ip):
        """Tenta pegar o MAC Address via tabela ARP local"""
        try:
            # Comando arp -a é rápido e não invasivo
            pid = subprocess.Popen(["arp", "-a", ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
            output, _ = pid.communicate(timeout=3)
            output = output.decode('latin-1')
            
            # Regex para encontrar MAC (Formato Windows e Linux)
            mac_regex = re.search(r"(([a-fA-F0-9]{2}[:-]){5}[a-fA-F0-9]{2})", output)
            if mac_regex:
                return mac_regex.group(1).replace('-', ':').upper()
        except:
            pass
        return None

    @staticmethod
    def get_vendor(mac):
        """Consulta API pública para descobrir fabricante pelo MAC"""
        if not mac: return "Desconhecido"
        
        prefix = mac[:8]
        if prefix in mac_vendor_cache:
            return mac_vendor_cache[prefix]
        
        try:
            # API rápida e gratuita para OUI
            url = f"https://api.macvendors.com/{mac}"
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                vendor = r.text.strip()
                mac_vendor_cache[prefix] = vendor
                return vendor
        except:
            pass
        return "Genérico"

    @staticmethod
    def check_port(ip, port):
        """Verifica se uma porta específica está aberta"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5) 
                return s.connect_ex((ip, port)) == 0
        except:
            return False

    @staticmethod
    def identify_type(ip, ttl, win_info):
        """Cruza dados para adivinhar o dispositivo"""
        device_type = "network"
        icon = "ph-globe"
        confidence = "Baixa"

        # 1. Se WMI funcionou, é Windows com certeza
        if win_info.get("status_code") == "ONLINE" and win_info.get("os") != "N/A":
            if "Server" in win_info.get("os", ""):
                return "server_windows", "ph-hard-drives", "Alta (WMI)"
            return "windows", "ph-windows-logo", "Alta (WMI)"

        # 2. Análise de Portas
        is_printer = DeviceIntelligence.check_port(ip, 9100) or DeviceIntelligence.check_port(ip, 515)
        is_web = DeviceIntelligence.check_port(ip, 80) or DeviceIntelligence.check_port(ip, 443)
        is_ssh = DeviceIntelligence.check_port(ip, 22)
        is_rtsp = DeviceIntelligence.check_port(ip, 554)
        
        # 3. Análise de TTL
        os_guess = "Desconhecido"
        if ttl:
            if 60 <= ttl <= 70: os_guess = "Linux/Unix Based"
            elif 120 <= ttl <= 130: os_guess = "Windows Based"
            elif ttl > 250: os_guess = "Cisco/Network"

        # 4. Decisão Final
        if is_printer:
            device_type = "printer"
            icon = "ph-printer"
            confidence = "Média (Porta 9100)"
        elif is_rtsp:
            device_type = "camera"
            icon = "ph-video-camera"
            confidence = "Média (Porta RTSP)"
        elif is_ssh and "Linux" in os_guess:
            device_type = "linux"
            icon = "ph-linux-logo"
            confidence = "Média (SSH + TTL)"
        elif "Windows" in os_guess:
            device_type = "windows_locked"
            icon = "ph-windows-logo"
            confidence = "Baixa (Apenas TTL)"
        elif is_web:
            device_type = "web_device"
            icon = "ph-wifi-high"
            confidence = "Baixa (Web)"
        
        return device_type, icon, confidence

# --- VARIÁVEIS DE ESTADO ---
scan_status = { 
    "running": False, 
    "results": load_db(), 
    "progress": 0, 
    "total": 0, 
    "scanned": 0, 
    "etr": "Calculando..." 
}
scan_lock = threading.Lock()
results_lock = threading.Lock()

def scheduler_loop():
    global schedule_config
    while True:
        # Recarrega a configuração a cada iteração para pegar mudanças
        schedule_config = load_schedule()
        
        if schedule_config.get("enabled"):
            now = time.time()
            last_run = schedule_config.get("last_run") or 0
            
            interval = int(schedule_config.get("interval", 60))
            unit = schedule_config.get("unit", "minutes")
            
            seconds = interval * 60
            if unit == "hours": seconds = interval * 3600
            elif unit == "days": seconds = interval * 86400
            
            if now - last_run >= seconds:
                if not scan_status["running"]:
                    subnet = schedule_config.get("subnet")
                    if subnet:
                        print(f"[SCHEDULER] Iniciando scan automático para {subnet}")
                        threading.Thread(target=scan_thread, args=(subnet,), daemon=True).start()
                        schedule_config["last_run"] = now
                        save_schedule(schedule_config)
                    else:
                        print("[SCHEDULER] AVISO: Subnet não configurada, pulando scan automático")
        
        time.sleep(30) # Verifica a cada 30 segundos

def rdp_gateway_loop():
    print("[RDP GATEWAY] Iniciando serviço auxiliar Node.js...")
    try:
        # Tenta rodar o gateway Node.js
        subprocess.Popen(["node", "rdp-gateway.js"], shell=True, creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        print(f"[RDP GATEWAY] Falha ao iniciar gateway: {e}")


def clean_wmi(text):
    if not text: return "N/A"
    if isinstance(text, bytes):
        try:
            text = text.decode('latin-1')
        except:
            text = str(text)
    
    # Remove o lixo do format:csv (Node, etc)
    lines = [line.strip() for line in text.replace('\r', '').split('\n') if line.strip()]
    if len(lines) < 2: return "N/A"
    
    # A segunda linha contém os dados no CSV do WMIC
    parts = lines[1].split(',')
    if len(parts) < 2: return "N/A"
    
    # Retorna o valor real (geralmente o último campo no CSV)
    return parts[-1].strip()

def get_full_audit(ip, user, password):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    ttl_val = None
    try:
        proc = subprocess.run(['ping', param, '1', '-w', '500', ip], capture_output=True, text=True, timeout=3, creationflags=CREATE_NO_WINDOW)
        if proc.returncode != 0: return None
        match = re.search(r"TTL=(\d+)", proc.stdout, re.I)
        if match: ttl_val = int(match.group(1))
    except: return None

    # Inicializa dados básicos
    info = { 
        "ip": ip, "hostname": "N/A", "os": "N/A", "model": "N/A", 
        "status_code": "OFFLINE", "user": "N/A", "ram": "N/A", 
        "cpu": "N/A", "uptime": "N/A", "bios": "N/A",
        "shares": [], "disks": [], "nics": [], "services": [], "errors": [],
        "printer_data": None
    }
    
    try: info["hostname"] = socket.gethostbyaddr(ip)[0]
    except: pass

    # Se for Windows (TTL típico), tenta auditoria via PowerShell
    if ttl_val and 120 <= ttl_val <= 130:
        try:
            # Tenta autenticar IPC$ antes de rodar o script para garantir acesso
            auth_cmd = f'net use \\\\{ip}\\IPC$ /user:{user} "{password}"'
            auth_res = subprocess.run(auth_cmd, shell=True, capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW)
            
            if auth_res.returncode == 0:
                info["status_code"] = "ONLINE"
                
                # Executa o script PowerShell avançado
                ps_script = resource_path(os.path.join("scripts", "audit_windows.ps1"))
                ps_cmd = [
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", 
                    "-File", ps_script, "-Ip", ip, 
                    "-User", user, "-Password", password,
                    "-TryFallback"
                ]
                
                audit_proc = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=15, creationflags=CREATE_NO_WINDOW)
                
                if audit_proc.returncode == 0 and audit_proc.stdout.strip():
                    try:
                        audit_data = json.loads(audit_proc.stdout.strip())
                        # Mapeamento do JSON para o dicionário 'info'
                        info["hostname"] = audit_data.get("hostname", info["hostname"])
                        info["os"] = audit_data.get("os", "N/A")
                        info["model"] = audit_data.get("model", "N/A")
                        info["user"] = audit_data.get("user", "N/A")
                        info["ram"] = f"{audit_data.get('ramGB')} GB" if audit_data.get("ramGB") != "N/A" else "N/A"
                        info["cpu"] = audit_data.get("cpu", "N/A")
                        info["uptime"] = audit_data.get("uptime", "N/A")
                        info["bios"] = audit_data.get("bios", "N/A")
                        info["shares"] = audit_data.get("shares", [])
                        info["disks"] = audit_data.get("disks", [])
                        info["nics"] = audit_data.get("nics", [])
                        info["services"] = audit_data.get("services", [])
                        info["errors"] = audit_data.get("errors", [])
                    except json.JSONDecodeError:
                        info["errors"].append("Erro ao processar JSON do PowerShell")
                else:
                    info["errors"].append(f"Script PowerShell falhou (Exit: {audit_proc.returncode})")
                
                # Limpa conexão IPC
                subprocess.run(f"net use \\\\{ip}\\IPC$ /delete /y", shell=True, capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            info["errors"].append(f"Erro na auditoria: {str(e)}")

    mac = DeviceIntelligence.get_mac_address(ip)
    vendor = DeviceIntelligence.get_vendor(mac)
    dtype, icon, conf = DeviceIntelligence.identify_type(ip, ttl_val, info)

    # Coleta SNMP se for impressora
    if dtype == "printer":
        p_audit = get_printer_data(ip)
        if p_audit:
            info["printer_data"] = p_audit
            info["model"] = p_audit.get("model", info["model"])
            info["serial"] = p_audit.get("serial", "N/A")

    return {
        "ip": ip, "hostname": info["hostname"], "device_type": dtype, "icon": icon, "vendor": vendor, "mac": mac or "-",
        "os_detail": info["os"] if info["os"] != "N/A" else f"Baseado em TTL={ttl_val}",
        "user": info["user"], "model": info["model"], "ram": info["ram"], "cpu": info["cpu"], "uptime": info["uptime"],
        "bios": info["bios"], "shares": info["shares"], "disks": info["disks"], 
        "nics": info["nics"], "services": info["services"], "errors": info["errors"],
        "printer_data": info["printer_data"],
        "confidence": conf,
        "last_updated_at": datetime.now().isoformat()
    }

def scan_thread(subnet):
    """
    Thread de scan de rede - DADOS SÃO PERMANENTES
    
    IMPORTANTE: Esta função NUNCA remove dispositivos antigos!
    - Se o IP já existe: ATUALIZA os dados
    - Se o IP é novo: ADICIONA à lista
    - IPs que não respondem: PERMANECEM na lista com dados antigos
    
    Args:
        subnet: Subnet a escanear (ex: '192.168.1.0/24')
    """
    scan_status["running"] = True
    # scan_status["results"] mantém TODOS os dados anteriores
    # NUNCA limpa ou remove dispositivos existentes
    scan_status["scanned"] = 0
    
    # Log do estado inicial
    initial_count = len(scan_status["results"])
    logger.info(f"Iniciando scan de {subnet} - Dispositivos existentes: {initial_count}")
    
    try:
        net = ipaddress.ip_network(subnet, strict=False)
        hosts = list(net.hosts())
        scan_status["total"] = len(hosts)
        
        logger.info(f"Escaneando {len(hosts)} IPs na subnet {subnet}")
        
        start = time.time()

        def worker(h):
            res = None
            try:
                res = get_full_audit(str(h), ADMIN_USER, ADMIN_PASS)
            except:
                pass
            finally:
                with scan_lock:
                    scan_status["scanned"] += 1
                    
                    # ETR calc
                    elapsed = time.time() - start
                    if scan_status["scanned"] > 0:
                        rate = elapsed / scan_status["scanned"]
                        rem = (scan_status["total"] - scan_status["scanned"]) * rate
                        scan_status["etr"] = f"{int(rem)}s"
            
            return res

        # Contadores para logging
        updated_count = 0
        added_count = 0

        with ThreadPoolExecutor(max_workers=40) as exc:
            for r in exc.map(worker, hosts):
                if r:
                    with scan_lock:
                        # Busca se o IP já existe na lista
                        found = False
                        for i, existing in enumerate(scan_status["results"]):
                            if existing['ip'] == r['ip']:
                                # ATUALIZA dispositivo existente
                                scan_status["results"][i] = r
                                found = True
                                updated_count += 1
                                logger.debug(f"Atualizado: {r['ip']}")
                                break
                        
                        if not found:
                            # ADICIONA novo dispositivo
                            scan_status["results"].append(r)
                            added_count += 1
                            logger.info(f"Novo dispositivo: {r['ip']} - {r.get('hostname', 'N/A')}")
                        
                        # Salva permanentemente a cada novo dispositivo encontrado
                        # Backup automático é feito pela função safe_json_save
                        save_db(scan_status["results"])
        
        # Log do resultado final
        final_count = len(scan_status["results"])
        logger.info(
            f"Scan concluído - Total: {final_count} | "
            f"Atualizados: {updated_count} | "
            f"Novos: {added_count} | "
            f"Preservados: {initial_count - updated_count}"
        )

    except Exception as e:
        logger.error(f"Erro no scan de {subnet}: {e}")
    finally:
        # IMPORTANTE: Este bloco finally garante que o scan pare no frontend
        scan_status["running"] = False
        scan_status["etr"] = "Concluído"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not check_setup():
        return redirect(url_for('setup_page'))
        
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Autenticação Segura com Encriptação
    from security import load_encrypted_json
    local_users = load_encrypted_json("users.json", fields_to_decrypt=["password"], default=[])
    
    for u in local_users:
        if u['username'] == username and u['password'] == password:
            if not u.get('is_active', True):
                return jsonify({'success': False, 'message': 'Esta conta está desativada. Entre em contato com o administrador.'})
                
            session['username'] = username
            session['role'] = u.get('role', 'user')
            session['is_master'] = u.get('is_master', False)
            session['permissions'] = u.get('permissions', {
                'type': 'view',
                'ad': True,
                'helpdesk': True
            })
            return jsonify({'success': True})
    
    # Se falhar local, tenta AD (se configurado)
    from ad_helper import authenticate_ad
    settings = load_general_settings()
    if settings.get('ad_enabled', True):
        if authenticate_ad(username, password):
            session['username'] = username
            session['role'] = 'user' # AD users are 'user' by default
            session['is_master'] = False
            session['permissions'] = {
                'type': 'view',
                'ad': True,
                'helpdesk': True
            }
            return jsonify({'success': True, 'ad': True})

    return jsonify({'success': False, 'message': 'Credenciais inválidas (Local ou AD).'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ROTAS DE PÁGINAS ---
@app.route('/')
def index():
    """Página de entrada (Landing Page para venda)"""
    if not check_setup():
        return redirect(url_for('setup_page'))
    return render_template('landing.html')

@app.route('/home')
def home():
    if not check_setup():
        return redirect(url_for('setup_page'))
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/setup', methods=['GET', 'POST'])
def setup_page():
    if check_setup():
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = request.json
        user = data.get('username')
        pw = data.get('password')
        if user and pw:
            # Salvar primeiro usuário de forma encriptada como MASTER
            from security import save_encrypted_json
            master_user = {
                "username": user, 
                "password": pw, 
                "role": "admin", 
                "is_master": True, 
                "is_active": True,
                "permissions": {
                    "type": "exec",
                    "ad": True,
                    "helpdesk": True
                }
            }
            save_encrypted_json("users.json", [master_user], fields_to_encrypt=["password"])
            return jsonify({"success": True})
    return render_template('setup.html')

@app.route('/license', methods=['GET', 'POST'])
@login_required
def license_page():
    if request.method == 'POST':
        pass # Mantendo compatibilidade se necessário, mas preferimos API agora
    
    # Renderiza a nova interface
    return render_template('license.html', hwid=lic_manager.get_hwid())

@app.route('/api/license/activate', methods=['POST'])
@login_required
def api_activate_license():
    data = request.json
    key = data.get('key')
    
    if not key:
        return jsonify({'success': False, 'message': 'Chave de licença vazia'})
        
    valid, user_data = lic_manager.validate_license(key)
    if valid:
        lic_manager.save_license(key)
        # O tracker foi removido para simplificação, trial local apenas
        return jsonify({'success': True, 'message': f'Licença ativada para {user_data.get("customer")}!'})
    else:
        return jsonify({'success': False, 'message': user_data})

# ===== ROTAS DO VENDEDOR (ADMIN SECRETO) =====
VENDOR_PASSWORD = os.environ.get("VENDOR_ADMIN_PASS", "VendorSecure2026!")

@app.route('/vendor/login', methods=['GET', 'POST'])
def vendor_login():
    if request.method == 'POST':
        data = request.json
        if data.get('password') == VENDOR_PASSWORD:
            session['vendor_authenticated'] = True
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Senha incorreta'})
    
    return '''
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>Vendor Login</title>
    <style>
        body { background: #0f172a; color: #fff; font-family: Arial; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .box { background: rgba(255,255,255,0.05); padding: 40px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); }
        input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.3); color: #fff; }
        button { width: 100%; padding: 12px; background: #6366f1; border: none; border-radius: 8px; color: #fff; font-weight: bold; cursor: pointer; }
    </style></head><body>
    <div class="box">
        <h2>🔐 Painel do Vendedor</h2>
        <input type="password" id="pass" placeholder="Senha de Acesso">
        <button onclick="login()">Entrar</button>
    </div>
    <script>
        async function login() {
            const res = await fetch('/vendor/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({password: document.getElementById('pass').value})
            });
            const data = await res.json();
            if(data.success) window.location.href = '/vendor/dashboard';
            else alert('Senha incorreta');
        }
    </script></body></html>
    '''

@app.route('/vendor/dashboard')
def vendor_dashboard():
    if not session.get('vendor_authenticated'):
        return redirect(url_for('vendor_login'))
    return render_template('vendor_dashboard.html')

@app.route('/vendor/api/stats')
def vendor_api_stats():
    if not session.get('vendor_authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(tracker.get_stats())

@app.route('/vendor/api/revoke', methods=['POST'])
def vendor_api_revoke():
    if not session.get('vendor_authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    customer = data.get('customer')
    
    if lic_manager.revoke_license(customer):
        return jsonify({'success': True, 'message': 'Licença revogada'})
    return jsonify({'success': False, 'message': 'Erro ao revogar'})

@app.route('/dashboard')
@login_required
def dashboard():
    # Check if user needs to see wizard (first time setup)
    if not session.get('wizard_completed') and session.get('is_master'):
        wizard_file = os.path.join(app_data_dir, 'wizard_completed.flag')
        if not os.path.exists(wizard_file):
            return redirect(url_for('wizard_page'))
    return render_template('dashboard.html')

@app.route('/wizard')
@login_required
def wizard_page():
    # Only master user can access wizard
    if not session.get('is_master'):
        return redirect(url_for('dashboard'))
    return render_template('wizard.html')

@app.route('/api/wizard/complete', methods=['POST'])
@login_required
def api_wizard_complete():
    # Mark wizard as completed
    wizard_file = os.path.join(app_data_dir, 'wizard_completed.flag')
    with open(wizard_file, 'w') as f:
        f.write('completed')
    session['wizard_completed'] = True
    return jsonify({'success': True})

@app.route('/scan')
@login_required
def scan_page():
    return render_template('scanner.html')

@app.route('/ad-users')
@login_required
@ad_required
@premium_required
def ad_users_page():
    return render_template('ad_users.html')

@app.route('/tickets')
@login_required
@tickets_required
@premium_required
def tickets_page():
    return render_template('tickets.html')

# --- ROTAS DE API ---
@app.route('/scan', methods=['POST'])
@login_required
@api_error_handler
def run_scan():
    """Inicia scan de rede com validação"""
    # Verificar rate limit
    username = session.get('username', 'unknown')
    if not rate_limiter.is_allowed(f"scan_{username}"):
        return jsonify({
            "success": False,
            "error": "rate_limit",
            "message": "Muitas requisições. Aguarde um momento."
        }), 429
    
    # Verificar se já está rodando
    if scan_status["running"]:
        return jsonify({
            "success": False,
            "error": "already_running",
            "message": "Scan já está em execução"
        }), 409
    
    # Validar dados de entrada
    data = request.json
    if not data:
        raise ValueError("Dados não fornecidos")
    
    subnet = data.get('subnet')
    if not subnet:
        raise ValueError("Subnet não fornecida")
    
    # Validar subnet
    valid, error_msg = validate_subnet(subnet)
    if not valid:
        raise ValueError(error_msg)
    
    logger.info(f"Iniciando scan da subnet {subnet} por {username}")
    
    # Iniciar scan em thread separada
    t = threading.Thread(target=scan_thread, args=(subnet,), daemon=True)
    t.start()
    
    return jsonify({
        "success": True,
        "message": "Scan iniciado com sucesso",
        "subnet": subnet
    })

@app.route('/status')
@login_required
def status():
    p = 0
    with scan_lock:
        if scan_status.get("total", 0) > 0:
            p = int((scan_status.get("scanned", 0) / scan_status["total"]) * 100)
    
    return jsonify({
        "running": scan_status["running"],
        "results": scan_status["results"],
        "progress": p,
        "total": scan_status["total"],
        "scanned": scan_status["scanned"],
        "etr": scan_status["etr"]
    })

@app.route('/api/schedule', methods=['GET', 'POST'])
@login_required
def api_schedule():
    global schedule_config
    if request.method == 'POST':
        data = request.json
        schedule_config.update({
            "enabled": data.get("enabled", False),
            "interval": data.get("interval", 60),
            "unit": data.get("unit", "minutes"),
            "subnet": data.get("subnet", "")
        })
        save_schedule(schedule_config)
        return jsonify({"success": True})
    return jsonify(schedule_config)

@app.route('/api/scan/individual', methods=['POST'])
@login_required
def api_scan_individual():
    data = request.json
    ip = data.get('ip')
    if not ip: return jsonify({"error": "IP missing"}), 400
    
    # Executa o audit em uma thread para não travar a UI se demorar, 
    # mas o usuário pediu "opção de atualização individual de cada ativo... quando eu clicar nele"
    # Geralmente auditoria individual pode ser síncrona se for rápida, mas vamos fazer rápida.
    
    res = get_full_audit(ip, ADMIN_USER, ADMIN_PASS)
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
    
    return jsonify({"success": False, "message": "Dispositivo Offline ou inacessível"})

@app.route('/ad-shares')
@login_required
@ad_required
def ad_shares_page():
    return render_template('ad_shares.html')

@app.route('/api/ad/shares')
@login_required
@ad_required
def api_ad_shares():
    # Retorna dados de armazenamento (Discos) em vez de shares
    disks = get_ad_storage()
    return jsonify(disks)

@app.route('/security')
@login_required
@ad_required
def security_page():
    return render_template('security.html')


@app.route('/api/sidebar/alerts-deprecated')
@login_required
def api_sidebar_alerts_deprecated():
    """Retorna contadores de alertas para a sidebar"""
    print("=== API Sidebar Alerts chamada ===")
    
    alerts = {
        'failed_logins': 0,
        'failed_logins_severity': 'none',
        'disk_warnings': 0,
        'disk_warnings_severity': 'none',
        'offline_servers': 0,
        'offline_servers_severity': 'none',
        'free_ips': 0,
        'free_ips_severity': 'none'
    }
    
    try:
        # 1. Logins Falhados (últimas 24h)
        print("Buscando failed logins...")
        try:
            failed_logins = get_failed_logins(24)
            print(f"Failed logins encontrados: {len(failed_logins) if failed_logins else 0}")
            
            if failed_logins and len(failed_logins) > 0:
                alerts['failed_logins'] = len(failed_logins)
                
                # Verificar severidade
                critical_count = sum(1 for f in failed_logins if 'bloqueada' in f.get('FailureReason', '').lower())
                if critical_count > 0 or len(failed_logins) > 50:
                    alerts['failed_logins_severity'] = 'critical'
                elif len(failed_logins) > 10:
                    alerts['failed_logins_severity'] = 'warning'
                
                print(f"Severidade: {alerts['failed_logins_severity']}")
        except Exception as e:
            print(f"Erro ao buscar failed logins: {e}")
        
        # 2. Discos com pouco espaço
        print("Buscando discos...")
        try:
            disks = get_ad_storage()
            print(f"Discos encontrados: {len(disks) if disks else 0}")
            
            if disks and len(disks) > 0:
                critical_disks = [d for d in disks if d.get('Status') == 'Online' and d.get('PctUsed', 0) > 90]
                warning_disks = [d for d in disks if d.get('Status') == 'Online' and 75 < d.get('PctUsed', 0) <= 90]
                offline_servers = [d for d in disks if d.get('Status') != 'Online']
                
                print(f"Discos críticos: {len(critical_disks)}, Atenção: {len(warning_disks)}, Offline: {len(offline_servers)}")
                
                if critical_disks:
                    alerts['disk_warnings'] = len(critical_disks)
                    alerts['disk_warnings_severity'] = 'critical'
                elif warning_disks:
                    alerts['disk_warnings'] = len(warning_disks)
                    alerts['disk_warnings_severity'] = 'warning'
                
                if offline_servers:
                    alerts['offline_servers'] = len(offline_servers)
                    alerts['offline_servers_severity'] = 'warning'
        except Exception as e:
            print(f"Erro ao buscar discos: {e}")
        
        # 3. IPs Livres
        print("Buscando IPs livres...")
        try:
            # Tenta pegar subnet da config do agendamento ou usa padrão vazio
            schedule = load_schedule()
            subnet = schedule.get('subnet')
            
            if subnet:
                free_data = get_free_ips(subnet, 7)
                if free_data and free_data.get('count', 0) > 0:
                    alerts['free_ips'] = free_data['count']
                    # Sempre mostrar em verde/info se houver IPs livres
                    alerts['free_ips_severity'] = 'info'
                    print(f"IPs livres: {alerts['free_ips']}")
            else:
                 alerts['free_ips'] = 0 # Nenhuma subnet configurada
        except Exception as e:
            print(f"Erro ao buscar IPs livres: {e}")
    
    except Exception as e:
        print(f"Erro geral ao obter alertas da sidebar: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"Retornando alertas: {alerts}")
    return jsonify(alerts)

@app.route('/ip-map')
@login_required
def ip_map_page():
    return render_template('ip_map.html')

@app.route('/api/ip-map')
@login_required
def api_ip_map():
    subnet = request.args.get('subnet')
    days = request.args.get('days', 7, type=int)
    
    ip_data = get_ip_map(subnet, days)
    return jsonify(ip_data)

@app.route('/api/ip-map/free')
@login_required
def api_free_ips():
    subnet = request.args.get('subnet')
    days = request.args.get('days', 7, type=int)
    
    free_data = get_free_ips(subnet, days)
    return jsonify(free_data)

@app.route('/api/ip-map/suggest')
@login_required
def api_suggest_ip():
    subnet = request.args.get('subnet')
    days = request.args.get('days', 7, type=int)
    
    suggestion = suggest_next_ip(subnet, days)
    return jsonify(suggestion if suggestion else {'error': 'Nenhum IP livre disponível'})

@app.route('/api/ad/users')
@login_required
@ad_required
def api_ad_users():
    users = get_ad_users()
    response = jsonify(users)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/api/ad/reset-password', methods=['POST'])
@login_required
@ad_required
def api_reset_password():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    success, message = reset_ad_password(username, password)
    return jsonify({'success': success, 'message': message})

@app.route('/ad-config')
@login_required
@ad_required
def ad_config_page():
    return render_template('ad_config.html')

@app.route('/api/ad/test-connection', methods=['POST'])
@login_required
def api_test_ad_connection():
    from ldap3 import Server, Connection, ALL, SIMPLE, NTLM
    from ldap3.core.exceptions import LDAPException
    import ssl
    
    data = request.json
    server_ip = data.get('server')
    domain = data.get('domain', '')
    admin_user = data.get('adminUser')
    admin_pass = data.get('adminPass')
    base_dn = data.get('baseDN', '')
    
    # Tenta inferir o nome curto NetBIOS (ex: FUNESASE.LOCAL -> FUNESASE)
    netbios_name = domain.split('.')[0].upper() if domain else ""
    
    # Tenta diferentes formatos de usuário
    user_formats = [
        f"{admin_user}@{domain}",         # UPN: usuario@dominio.local
        f"{netbios_name}\\{admin_user}",  # NetBIOS Curto: DOMINIO\usuario
        f"{domain}\\{admin_user}",        # NetBIOS Longo: dominio.local\usuario
        f"cn={admin_user},{base_dn}" if base_dn else None, # DN completo
        admin_user                        # Apenas o nome
    ]
    
    errors = []
    logger.info(f"[AD TEST] Iniciando testes para {server_ip} (Usuário: {admin_user})")
    
    for user_dn in filter(None, user_formats):
        # Tenta em ambas as portas
        for port in [389, 636]:
            # Tenta SIMPLE e NTLM
            for auth_method in [SIMPLE, NTLM]:
                use_ssl = (port == 636)
                tls = None
                if use_ssl:
                    try:
                        tls_ctx = ssl.create_default_context()
                        tls_ctx.check_hostname = False
                        tls_ctx.verify_mode = ssl.CERT_NONE
                        from ldap3 import Tls
                        tls = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
                    except: pass

                try:
                    # Configura servidor com timeout curto para não travar a UI
                    ldap_server = Server(server_ip, port=port, use_ssl=use_ssl, get_info=ALL, tls=tls, connect_timeout=5)
                    conn = Connection(ldap_server, user=user_dn, password=admin_pass, authentication=auth_method, receive_timeout=5)
                    
                    logger.debug(f"[AD TEST] Tentando: {user_dn} | Port: {port} | Auth: {auth_method}")
                    
                    if conn.bind():
                        method_name = "SIMPLE" if auth_method == SIMPLE else "NTLM"
                        protocol = "SSL" if use_ssl else "LDAP"
                        logger.info(f"[AD TEST] SUCESSO! {user_dn} via {protocol} ({method_name})")
                        
                        conn.unbind()
                        try:
                            from ad_helper import record_ad_success
                            record_ad_success()
                        except: pass
                        
                        return jsonify({
                            'success': True, 
                            'message': f'Conexão OK! Autenticado via {method_name} ({protocol}) usando formato {user_dn}.'
                        })
                    else:
                        err_msg = f"{user_dn} ({port}/{auth_method}): {conn.result.get('description', 'Falha no Bind')}"
                        errors.append(err_msg)
                except Exception as e:
                    errors.append(f"{user_dn} ({port}): {str(e)[:60]}")
    
    # Se nenhum formato funcionou
    last_err = errors[-1] if errors else "Sem resposta do servidor"
    logger.error(f"[AD TEST] FALHA TOTAL. Erros: {len(errors)}. Último: {last_err}")
    
    return jsonify({
        'success': False, 
        'message': f'Falha na autenticação após {len(errors)} tentativas. Erro técnico: {last_err}'
    })

@app.route('/api/ad/save-config', methods=['POST'])
@login_required
def api_save_ad_config():
    data = request.json
    
    # Salva em arquivo JSON
    config = {
        'server': data.get('server'),
        'domain': data.get('domain'),
        'baseDN': data.get('baseDN'),
        'adminUser': data.get('adminUser'),
        'adminPass': data.get('adminPass')
    }
    
    try:
        from security import save_encrypted_json
        save_encrypted_json('ad_config.json', config, fields_to_encrypt=['adminPass'])
        return jsonify({'success': True, 'message': 'Configuração salva (Encriptada)'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ad/status')
@login_required
def api_ad_status():
    from ad_helper import TEST_MODE, get_last_ad_connection
    
    config = None
    configured = False
    
    if os.path.exists('ad_config.json'):
        try:
            from security import load_encrypted_json
            config = load_encrypted_json("ad_config.json", fields_to_decrypt=["adminPass"])
            configured = True
            # Mask password for frontend
            if config and config.get('adminPass'):
                config['adminPass'] = "" # Never send password to frontend
        except:
            pass
    
    response = jsonify({
        'testMode': TEST_MODE,
        'configured': configured,
        'config': config,
        'lastConnection': get_last_ad_connection()
    })
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# --- NOVAS ROTAS DE GESTÃO (PREMIUM) ---
@app.route('/settings/users')
@login_required
def settings_users():
    return render_template('system_users.html')

@app.route('/api/system/users', methods=['GET'])
@login_required
def api_list_system_users():
    from security import load_encrypted_json
    users = load_encrypted_json("users.json", fields_to_decrypt=["password"], default=[])
    # Sanitize: Remove passwords before sending to frontend
    sanitized = []
    for u in users:
        sanitized.append({
            "username": u.get("username"),
            "role": u.get("role", "user"),
            "is_master": u.get("is_master", False),
            "is_active": u.get("is_active", True),
            "permissions": u.get("permissions", {
                "type": "view",
                "ad": True,
                "helpdesk": True
            })
        })
    return jsonify(sanitized)

@app.route('/api/system/users', methods=['POST'])
@login_required
@admin_required
def api_create_system_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    is_active = data.get('is_active', True)
    permissions = data.get('permissions', {
        "type": "view",
        "ad": True,
        "helpdesk": True
    })
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Campos obrigatórios faltando'})
        
    from security import load_encrypted_json, save_encrypted_json
    users = load_encrypted_json("users.json", fields_to_decrypt=["password"], default=[])
    
    # Check duplicate
    if any(u['username'] == username for u in users):
        return jsonify({'success': False, 'message': 'Usuário já existe'})
        
    # VERIFICAÇÃO DE LIMITE DE USUÁRIOS (PRO VS FREE)
    if len(users) >= lic_manager.get_user_limit():
        return jsonify({
            'success': False, 
            'message': f'Limite de usuários atingido ({lic_manager.get_user_limit()}). Atualize para Premium para usuários ilimitados.'
        }), 403
        
    users.append({
        "username": username, 
        "password": password, 
        "role": role,
        "is_master": False,
        "is_active": is_active,
        "permissions": permissions
    })
    save_encrypted_json("users.json", users, fields_to_encrypt=["password"])
    
    return jsonify({'success': True})

@app.route('/api/system/users/<username>', methods=['PUT'])
@login_required
@admin_required
def api_update_system_user(username):
    data = request.json
    password = data.get('password') # Optional (empty means no change)
    role = data.get('role')
    is_active = data.get('is_active')
    permissions = data.get('permissions')
    
    from security import load_encrypted_json, save_encrypted_json
    users = load_encrypted_json("users.json", fields_to_decrypt=["password"], default=[])
    
    found = False
    for u in users:
        if u['username'] == username:
            # BLOQUEIO USUÁRIO MASTER
            if u.get('is_master', False):
                # Se for master, não pode alterar senha por aqui (conforme requisito 2)
                if password:
                    return jsonify({'success': False, 'message': 'Não é permitido alterar a senha do usuário Master através deste painel.'}), 403
                # Master é sempre admin e sempre ativo
                u['role'] = 'admin'
                u['is_active'] = True
            else:
                if password:
                    u['password'] = password
                if role:
                    u['role'] = role
                if is_active is not None:
                    u['is_active'] = is_active

            # Permissões podem ser alteradas para qualquer um (exceto master? Master deve ter tudo)
            if permissions and not u.get('is_master', False):
                u['permissions'] = permissions
            
            found = True
            break
            
    if found:
        save_encrypted_json("users.json", users, fields_to_encrypt=["password"])
        return jsonify({'success': True})
        
    return jsonify({'success': False, 'message': 'Usuário não encontrado'})

@app.route('/api/system/users/<username>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_system_user(username):
    # Prevent self-deletion
    if username == session.get('username'):
        return jsonify({'success': False, 'message': 'Você não pode excluir a si mesmo'})
        
    from security import load_encrypted_json, save_encrypted_json
    users = load_encrypted_json("users.json", fields_to_decrypt=["password"], default=[])
    
    original_len = len(users)
    users = [u for u in users if u['username'] != username]
    
    if len(users) < original_len:
        save_encrypted_json("users.json", users, fields_to_encrypt=["password"])
        return jsonify({'success': True})
        
    return jsonify({'success': False, 'message': 'Usuário não encontrado'})

@app.route('/api/system/uninstall', methods=['POST'])
@login_required
def api_system_uninstall():
    """Nuclear option: Deleta todos os dados e encerra o sistema"""
    # Só o usuário master pode desinstalar totalmente
    if not session.get('is_master'):
        return jsonify({'success': False, 'message': 'Apenas o usuário Master pode desinstalar o sistema.'}), 403
        
    try:
        # 1. Cria script de limpeza (Batch) que espera o processo fechar e limpa tudo
        cleanup_script = os.path.join(os.environ.get('TEMP'), 'netaudit_cleanup.bat')
        exe_path = sys.executable
        app_data = app_data_dir
        
        # O script vai:
        # 1. Esperar 5 segundos (tempo do app fechar)
        # 2. Deletar a pasta do AppData
        # 3. Se for EXE, deletar o próprio executável (opcional - perigoso se estiver no desktop)
        # 4. Deletar a si mesmo
        with open(cleanup_script, 'w') as f:
            f.write(f'''@echo off
timeout /t 5 /nobreak > nul
echo Limpando dados do NetAudit...
rd /s /q "{app_data}"
echo Dados removidos com sucesso.
del "%~f0"
''')

        # 2. Executa o script em background
        subprocess.Popen(['cmd.exe', '/c', cleanup_script], 
                       creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0)
        
        # 3. Agenda o encerramento do app
        def kill_app():
            time.sleep(2)
            os._exit(0)
            
        threading.Thread(target=kill_app).start()
        
        return jsonify({'success': True, 'message': 'Sistema em processo de desinstalação. O programa irá fechar em instantes.'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao preparar desinstalação: {str(e)}'})



@app.route('/api/ad/users/<username>/unlock', methods=['POST'])
@login_required
@admin_required
def api_unlock_user(username):
    success, msg = unlock_user_account(username)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/ad/users/<username>/status', methods=['POST'])
@login_required
@admin_required
def api_toggle_status(username):
    data = request.json
    enable = data.get('enable', True)
    success, msg = toggle_user_status(username, enable)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/ad/users/<username>/update', methods=['POST'])
@login_required
@admin_required
def api_update_user(username):
    data = request.json
    # data ex: {'telephoneNumber': '...', 'title': '...'}
    success, msg = update_ad_attributes(username, data)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/ad/groups', methods=['GET'])
@login_required
def api_list_groups():
    groups = get_all_ad_groups()
    return jsonify(groups)

@app.route('/api/ad/groups/membership', methods=['POST'])
@login_required
@admin_required
def api_manage_group():
    data = request.json
    username = data.get('username')
    group = data.get('group')
    action = data.get('action') # 'add' or 'remove'
    
    success, msg = manage_group_membership(username, group, action)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/scan/update-device', methods=['POST'])
@login_required
@admin_required
def api_update_device():
    data = request.json
    ip = data.get('ip')
    
    if not ip: return jsonify({'success': False, 'message': 'IP missing'})
    
    with scan_lock:
        found = False
        for device in scan_status["results"]:
            if device['ip'] == ip:
                # Update allowed fields
                if 'hostname' in data: device['hostname'] = data['hostname']
                if 'device_type' in data: device['device_type'] = data['device_type']
                if 'custom_location' in data: device['custom_location'] = data['custom_location']
                if 'custom_notes' in data: device['custom_notes'] = data['custom_notes']
                # If changing type, update icon
                if 'device_type' in data:
                    dtype = data['device_type'].lower()
                    if 'printer' in dtype: device['icon'] = 'ph-printer'
                    elif 'windows' in dtype: device['icon'] = 'ph-windows-logo'
                    elif 'linux' in dtype: device['icon'] = 'ph-linux-logo'
                    elif 'camera' in dtype: device['icon'] = 'ph-video-camera'
                    else: device['icon'] = 'ph-question'
                
                found = True
                break
        
        if found:
            save_db(scan_status["results"])
            return jsonify({'success': True, 'message': 'Dados do dispositivo atualizados!'})
        else:
            return jsonify({'success': False, 'message': 'Dispositivo não encontrado no histórico'})



@app.route('/api/cache/clear', methods=['POST'])
@login_required
@admin_required
def api_clear_cache():
    from cache_helper import clear_cache
    clear_cache()
    return jsonify({'success': True, 'message': 'Cache limpo com sucesso!'})

@app.route('/api/schedule', methods=['GET'])
@login_required
def api_get_schedule():
    """Retorna a configuração atual do scan automático"""
    global schedule_config
    return jsonify(schedule_config)

@app.route('/api/schedule', methods=['POST'])
@login_required
@admin_required
def api_save_schedule():
    """Salva a configuração do scan automático"""
    global schedule_config
    data = request.get_json()
    
    schedule_config['enabled'] = data.get('enabled', False)
    schedule_config['interval'] = int(data.get('interval', 60))
    schedule_config['unit'] = data.get('unit', 'minutes')
    schedule_config['subnet'] = data.get('subnet', '')
    
    save_schedule(schedule_config)
    
    return jsonify({
        'success': True,
        'message': 'Configuração salva com sucesso!',
        'config': schedule_config
    })

# --- NOVAS ROTAS PARA CREDENCIAIS INDIVIDUAIS ---
@app.route('/api/user/credentials/ad', methods=['POST'])
@login_required
def api_save_user_ad_credentials():
    data = request.json
    username = session.get('username')
    
    from security import load_encrypted_json, save_encrypted_json
    users = load_encrypted_json("users.json", fields_to_decrypt=["password"], default=[])
    
    for u in users:
        if u['username'] == username:
            if 'credentials' not in u: u['credentials'] = {}
            u['credentials']['ad'] = {
                'server': data.get('server'),
                'domain': data.get('domain'),
                'baseDN': data.get('baseDN'),
                'adminUser': data.get('adminUser'),
                'adminPass': data.get('adminPass')
            }
            save_encrypted_json("users.json", users, fields_to_encrypt=["password"])
            return jsonify({'success': True, 'message': 'Credenciais AD salvas para seu perfil.'})
            
    return jsonify({'success': False, 'message': 'Usuário não encontrado'})

@app.route('/api/user/credentials/glpi', methods=['POST'])
@login_required
def api_save_user_glpi_credentials():
    data = request.json
    username = session.get('username')
    
    # O GLPI já tem suporte no glpi_helper, mas vamos garantir que fique no users.json também 
    # ou apenas usar o glpi_helper. Vamos usar o glpi_helper para consistência com o código existente.
    from glpi_helper import save_glpi_config
    
    config = {
        'url': data.get('url'),
        'app_token': data.get('app_token'),
        'user_token': data.get('user_token'),
        'auth_user': data.get('auth_user'),
        'auth_pass': data.get('auth_pass')
    }
    
    if save_glpi_config(username, config):
        return jsonify({'success': True, 'message': 'Credenciais Helpdesk salvas para seu perfil.'})
    return jsonify({'success': False, 'message': 'Erro ao salvar credenciais Helpdesk.'})


# ========== SCHEDULER BACKGROUND THREAD ==========
def scheduler_loop():
    """Thread em background que executa scans automáticos baseado na configuração"""
    global schedule_config
    while True:
        try:
            if schedule_config.get("enabled"):
                now = time.time()
                last_run = schedule_config.get("last_run") or 0
                
                interval = int(schedule_config.get("interval", 60))
                unit = schedule_config.get("unit", "minutes")
                
                # Converte para segundos
                seconds = interval * 60
                if unit == "hours": 
                    seconds = interval * 3600
                elif unit == "days": 
                    seconds = interval * 86400
                
                # Verifica se é hora de executar
                if now - last_run >= seconds:
                    if not scan_status["running"]:
                        subnet = schedule_config.get("subnet")
                        if subnet:
                            print(f"[SCHEDULER] Iniciando scan automático para {subnet}")
                            threading.Thread(target=scan_thread, args=(subnet,), daemon=True).start()
                            schedule_config["last_run"] = now
                            save_schedule(schedule_config)
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
        
        time.sleep(30)  # Verifica a cada 30 segundos

# ===== DASHBOARD API ROUTES =====
@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """Retorna estatísticas detalhadas para os dashboards visuais (otimizado com threads)"""
    try:
        username = session.get('username')
        start_time = time.time()
        
        # Funções wrappers para o ThreadPool
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

        # Execução paralela
        settings = load_general_settings()
        ad_enabled = settings.get('ad_enabled', True)
        tickets_enabled = settings.get('tickets_enabled', True)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_users = executor.submit(fetch_users) if ad_enabled else None
            future_tickets = executor.submit(fetch_tickets) if tickets_enabled else None
            
            # Enquanto threads rodam, processamos os dados locais (memória)
            # 2. Dados do Scanner (SO e Tipos)
            os_dist = {}
            type_dist = {}
            online_devices = scan_status.get("results", [])
            
            for d in online_devices:
                # Distribuição de SO
                os_name = d.get('os_detail', 'N/A')
                if 'Windows' in os_name: os_name = 'Windows'
                elif 'Linux' in os_name: os_name = 'Linux'
                elif 'Printer' in os_name or d.get('device_type') == 'printer': os_name = 'Impressoras'
                elif os_name == 'N/A': os_name = 'Outros/Rede'
                
                os_dist[os_name] = os_dist.get(os_name, 0) + 1
                
                # Distribuição de Tipos
                dtype = d.get('device_type', 'network')
                type_dist[dtype] = type_dist.get(dtype, 0) + 1
            
            # Coleta resultados das threads (timeout de 5s para não travar)
            users = future_users.result(timeout=10) if future_users else []
            tickets = future_tickets.result(timeout=10) or []

        # Processamento final
        total_users = len(users)
        active_users = len([u for u in users if u.get('enabled', False)])
        
        ticket_stats = {"new": 0, "processing": 0, "solved": 0, "closed": 0}
        if isinstance(tickets, list):
            for t in tickets:
                sid = t.get('status')
                if sid == 1: ticket_stats["new"] += 1
                elif sid in [2, 3, 4]: ticket_stats["processing"] += 1
                elif sid == 5: ticket_stats["solved"] += 1
                elif sid == 6: ticket_stats["closed"] += 1

        elapsed = time.time() - start_time
        logger.info(f"Dashboard stats carregado em {elapsed:.2f}s")

        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'os_distribution': os_dist,
            'device_types': type_dist,
            'ticket_stats': ticket_stats,
            'online_count': len(online_devices)
        })
    except Exception as e:
        logger.error(f"Erro ao buscar stats da dashboard: {e}")
        return jsonify({
            'error': str(e),
            'total_users': 0,
            'active_users': 0,
            'os_distribution': {},
            'device_types': {},
            'ticket_stats': {}
        })

@app.route('/api/security/failed-logins')
@login_required
def api_failed_logins():
    """Retorna contagem de logins falhados"""
    try:
        hours = request.args.get('hours', 24, type=int)
        from ad_helper import get_failed_logins
        
        failed_logins = get_failed_logins(hours)
        
        if failed_logins is None:
            failed_logins = []
        
        count = len(failed_logins) if isinstance(failed_logins, list) else 0
        
        return jsonify({
            'success': True,
            'count': count,
            'logins': failed_logins[:10] if failed_logins else []  # Top 10
        })
    except Exception as e:
        logger.error(f"Erro ao buscar logins falhados: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'count': 0,
            'logins': [],
            'error': str(e)
        })

@app.route('/api/sidebar/alerts')
@login_required
def api_sidebar_alerts_optimized():
    """Retorna alertas para a sidebar e dashboard (otimizado com threads)"""
    try:
        start_time = time.time()
        # Verifica se existe sessão (evita erro de contexto em threads de background)
        try:
            username = session.get('username')
        except RuntimeWarning:
            username = "system"
        except Exception:
            username = "system"
        
        alerts = {
            'full_disks': 0, 'offline_servers': 0, 'failed_logins': 0, 'total_alerts': 0, 'new_tickets': 0,
            'failed_logins_severity': 'none', 'disk_warnings': 0, 'disk_warnings_severity': 'none',
            'offline_servers_severity': 'none', 'free_ips': 0, 'free_ips_severity': 'none'
        }

        # Wrappers para execução segura
        def safe_disks(): 
            try: from ad_helper import get_disk_alerts; return get_disk_alerts()
            except: return []

        def safe_offline():
            try: from ad_helper import get_offline_servers; return get_offline_servers()
            except: return []

        def safe_logins():
            try: from ad_helper import get_failed_logins; return get_failed_logins()
            except: return []

        def safe_ips():
            try: from ip_manager import get_free_ips; return get_free_ips()
            except: return []

        def safe_tickets():
            try: from glpi_helper import get_my_tickets; return get_my_tickets(username)
            except: return []

        # Execução Paralela
        settings = load_general_settings()
        ad_enabled = settings.get('ad_enabled', True)
        tickets_enabled = settings.get('tickets_enabled', True)

        with ThreadPoolExecutor(max_workers=5) as executor:
            f_disks = executor.submit(safe_disks) if ad_enabled else None
            f_offline = executor.submit(safe_offline) if ad_enabled else None
            f_logins = executor.submit(safe_logins) if ad_enabled else None
            f_ips = executor.submit(safe_ips)
            f_tickets = executor.submit(safe_tickets) if tickets_enabled else None

            # Coleta (Timeout de 8s para garantir responsividade)
            disk_alerts = f_disks.result(timeout=10) if f_disks else []
            offline_servers = f_offline.result(timeout=10) if f_offline else []
            failed_logins = f_logins.result(timeout=10) if f_logins else []
            free_ips_list = f_ips.result(timeout=10) or []
            tickets_result = f_tickets.result(timeout=10) if f_tickets else []

        # Processamento dos resultados
        # 1. Discos
        disk_count = len(disk_alerts)
        alerts['full_disks'] = disk_count
        alerts['disk_warnings'] = disk_count
        if disk_count > 0: alerts['disk_warnings_severity'] = 'critical'

        # 2. Offline
        offline_count = len(offline_servers)
        alerts['offline_servers'] = offline_count
        if offline_count > 0: alerts['offline_servers_severity'] = 'critical'

        # 3. Logins
        failed_count = len(failed_logins)
        alerts['failed_logins'] = failed_count
        if failed_count > 0: alerts['failed_logins_severity'] = 'warning'

        # 4. IPs
        free_count = len(free_ips_list)
        if free_count > 0:
            alerts['free_ips'] = free_count
            alerts['free_ips_severity'] = 'info'

        # 5. Tickets
        new_tickets_count = 0
        if isinstance(tickets_result, list):
            new_tickets_count = sum(1 for t in tickets_result if t.get('status') == 1)
        alerts['new_tickets'] = new_tickets_count

        # Total
        alerts['total_alerts'] = disk_count + offline_count + new_tickets_count

        elapsed = time.time() - start_time
        logger.info(f"Sidebar alerts carregado em {elapsed:.2f}s")
        
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Erro ao buscar alertas: {e}")
        return jsonify({
            'full_disks': 0, 'offline_servers': 0, 'failed_logins': 0, 'total_alerts': 0,
            'disk_warnings': 0, 'failed_logins_severity': 'none'
        })

@app.route('/settings')
@login_required
@admin_required
def settings_page():
    return render_template('settings.html')

@app.route('/api/settings/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.json
    current_pw = data.get('currentPassword')
    new_pw = data.get('newPassword')
    username = session.get('username')

    if not current_pw or not new_pw:
        return jsonify({'success': False, 'message': 'Preencha todos os campos'})

    from security import load_encrypted_json, save_encrypted_json
    users = load_encrypted_json("users.json", fields_to_decrypt=["password"], default=[])
    user_found = False
    
    for u in users:
        if u['username'] == username:
            # BLOQUEIO MASTER (Requisito 2)
            if u.get('is_master', False):
                return jsonify({'success': False, 'message': 'A senha do usuário Master é protegida e não pode ser alterada.'})

            if u['password'] == current_pw:
                u['password'] = new_pw
                user_found = True
                break
            else:
                return jsonify({'success': False, 'message': 'Senha atual incorreta'})

    if user_found:
        save_encrypted_json("users.json", users, fields_to_encrypt=["password"])
        return jsonify({'success': True, 'message': 'Senha alterada com sucesso!'})
    
    return jsonify({'success': False, 'message': 'Usuário não encontrado'})

@app.route('/api/ip-map/free')
@login_required
def api_ip_map_free():
    """Retorna contagem de IPs livres"""
    try:
        from ip_manager import get_free_ips
        free_ips = get_free_ips()
        
        count = len(free_ips) if free_ips else 0
        
        return jsonify({
            'count': count,
            'ips': free_ips[:20] if free_ips else []  # Top 20
        })
    except Exception as e:
        logger.error(f"Erro ao buscar IPs livres: {e}")
        return jsonify({
            'count': 0,
            'ips': []
        })

# ===== GLPI INTEGRATION ROUTES =====
@app.route('/api/glpi/config', methods=['GET', 'POST'])
@login_required
def api_glpi_config():
    from glpi_helper import load_glpi_config, save_glpi_config, test_connection
    username = session.get('username')
    
    if request.method == 'GET':
        config = load_glpi_config(username)
        if config:
            # Não retornar tokens/senhas reais, apenas indicação
            return jsonify({
                'configured': True,
                'url': config.get('url'),
                'username': config.get('auth_user') or 'Token based'
            })
        return jsonify({'configured': False})

    # POST: Salvar configuração
    data = request.json
    url = data.get('url')
    app_token = data.get('app_token')
    user_token = data.get('user_token')
    login = data.get('login')
    password = data.get('password')
    
    if not url or not app_token:
        return jsonify({'success': False, 'message': 'URL e App-Token são obrigatórios'})
        
    # Testar conexão
    success, message = test_connection(url, app_token, user_token, login, password)
    
    if success:
        config = {
            'url': url,
            'app_token': app_token,
            'user_token': user_token,
            'auth_user': login,
            'auth_pass': password
        }
        save_glpi_config(username, config)
        return jsonify({'success': True, 'message': 'Conexão realizada com sucesso!'})
    else:
        return jsonify({'success': False, 'message': message})

@app.route('/api/glpi/tickets')
@login_required
def api_glpi_tickets():
    from glpi_helper import get_my_tickets
    username = session.get('username')
    status_filter = request.args.get('status', 'not_solved') # not_solved, solved, specific ID
    
    tickets = get_my_tickets(username)
    
    if isinstance(tickets, dict) and 'error' in tickets:
        return jsonify({'success': False, 'error': tickets['error']})
    
    # Filtragem Python (Status IDs: 1=New, 2=Processing/Assign, 3=Planned, 4=Pending, 5=Solved, 6=Closed)
    filtered = []
    if isinstance(tickets, list):
        for t in tickets:
            sid = t.get('status', 0)
            
            # Lógica de Filtro
            if status_filter == 'not_solved':
                if sid in [1, 2, 3, 4]: filtered.append(t)
            elif status_filter == 'solved':
                if sid in [5, 6]: filtered.append(t)
            elif status_filter == 'closed':
                if sid == 6: filtered.append(t)
            else: # 'all'
                filtered.append(t)
                
    return jsonify({'success': True, 'tickets': filtered})

@app.route('/api/glpi/stats')
@login_required
def api_glpi_stats():
    from glpi_helper import get_glpi_stats
    username = session.get('username')
    stats = get_glpi_stats(username)
    return jsonify(stats)

@app.route('/api/glpi/categories')
@login_required
def api_glpi_categories():
    from glpi_helper import get_glpi_categories
    username = session.get('username')
    cats = get_glpi_categories(username)
    return jsonify(cats)

@app.route('/api/glpi/locations')
@login_required
def api_glpi_locations():
    from glpi_helper import get_glpi_locations
    username = session.get('username')
    locs = get_glpi_locations(username)
    return jsonify(locs)

@app.route('/api/glpi/ticket/<int:ticket_id>/followup', methods=['POST'])
@login_required
def api_glpi_followup(ticket_id):
    from glpi_helper import add_ticket_followup
    username = session.get('username')
    data = request.json
    content = data.get('content')
    
    if not content:
        return jsonify({'success': False, 'message': 'Conteúdo vazio'})
        
    res = add_ticket_followup(username, ticket_id, content)
    return jsonify(res)

@app.route('/api/glpi/ticket/<int:ticket_id>/solution', methods=['POST'])
@login_required
def api_glpi_solution(ticket_id):
    from glpi_helper import add_ticket_solution
    username = session.get('username')
    data = request.json
    content = data.get('content')
    
    if not content:
        return jsonify({'success': False, 'message': 'Conteúdo vazio'})
        
    res = add_ticket_solution(username, ticket_id, content)
    return jsonify(res)

@app.route('/api/glpi/tickets/create', methods=['POST'])
@login_required
def api_glpi_create_ticket():
    from glpi_helper import create_ticket
    username = session.get('username')
    data = request.json
    title = data.get('title')
    content = data.get('content')
    
    extra = {
        'category': data.get('category'),
        'urgency': data.get('urgency'),
        'impact': data.get('impact'),
        'location': data.get('location')
    }
    
    if not title or not content:
        return jsonify({'success': False, 'message': 'Título e Descrição são obrigatórios'})
        
    res = create_ticket(username, title, content, extra_params=extra)
    return jsonify(res)

@app.route('/api/glpi/ticket/<int:ticket_id>')
@login_required
def api_glpi_ticket_detail(ticket_id):
    from glpi_helper import get_ticket_details
    username = session.get('username')
    
    details = get_ticket_details(username, ticket_id)
    
    if isinstance(details, dict) and 'error' in details:
        return jsonify({'success': False, 'error': details['error']})
        
    return jsonify({'success': True, 'ticket': details})


def start_background_services():
    """Inicia serviços de background (Scheduler, RDP Gateway, Atalhos)"""
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    
    rdp_thread = threading.Thread(target=rdp_gateway_loop, daemon=True)
    rdp_thread.start()

    try:
        create_desktop_shortcut()
    except:
        pass

if __name__ == '__main__':
    # Inicia a thread do scheduler em background
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    
    # Inicia Gateway RDP
    rdp_thread = threading.Thread(target=rdp_gateway_loop, daemon=True)
    rdp_thread.start()

    # Cria atalho na área de trabalho se necessário
    create_desktop_shortcut()

    # Abrir navegador automaticamente se for o EXE (Apenas se executado diretamente, launcher faz isso)
    if getattr(sys, 'frozen', False):
        def open_browser():
            time.sleep(2)
            webbrowser.open('http://127.0.0.1:5000')
        threading.Thread(target=open_browser, daemon=True).start()
    
    # Servidor de Produção para Windows (Waitress)
    if getattr(sys, 'frozen', False):
        try:
            from waitress import serve
            print("[INFO] Iniciando NetAudit Enterprise em http://localhost:5000")
            serve(app, host='0.0.0.0', port=5000, threads=12)
        except ImportError:
            app.run(host='0.0.0.0', port=5000)
    else:
        # Modo desenvolvimento SEM auto-reload (evita OSError 10038 no Windows)
        print("[INFO] Servidor iniciado em modo desenvolvimento")
        print("[INFO] Auto-reload DESABILITADO (evita erros no Windows)")
        print("[INFO] Para aplicar mudanças, reinicie manualmente o servidor")
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
