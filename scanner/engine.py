import ipaddress
import socket
import subprocess
import threading
import time
import platform
import json
import os
import re
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from shared_state import scan_status, scan_lock, update_scan_status
from utils import logger, resource_path, safe_json_save
from snmp_helper import get_printer_data

# Windows specific
CREATE_NO_WINDOW = 0x08000000 if platform.system() == 'Windows' else 0

class DeviceIntelligence:
    @staticmethod
    def get_mac_address(ip):
        """Tenta pegar o MAC Address via tabela ARP local"""
        try:
            pid = subprocess.Popen(["arp", "-a", ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
            output, _ = pid.communicate(timeout=3)
            output = output.decode('latin-1')
            mac_regex = re.search(r"(([a-fA-F0-9]{2}[:-]){5}[a-fA-F0-9]{2})", output)
            if mac_regex:
                return mac_regex.group(1).replace('-', ':').upper()
        except:
            pass
        return None

    @staticmethod
    def get_vendor(mac):
        """Consulta API pública para descobrir fabricante pelo MAC"""
        if not mac or mac == "-": return "Desconhecido"
        try:
            url = f"https://api.macvendors.com/{mac}"
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return r.text.strip()
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

        if win_info.get("status_code") == "ONLINE" and win_info.get("os") != "N/A":
            if "Server" in win_info.get("os", ""):
                return "server_windows", "ph-hard-drives", "Alta (WMI)"
            return "windows", "ph-windows-logo", "Alta (WMI)"

        is_printer = DeviceIntelligence.check_port(ip, 9100) or DeviceIntelligence.check_port(ip, 515)
        is_web = DeviceIntelligence.check_port(ip, 80) or DeviceIntelligence.check_port(ip, 443)
        is_ssh = DeviceIntelligence.check_port(ip, 22)
        is_rtsp = DeviceIntelligence.check_port(ip, 554)
        
        os_guess = "Desconhecido"
        if ttl:
            if 60 <= ttl <= 70: os_guess = "Linux/Unix Based"
            elif 120 <= ttl <= 130: os_guess = "Windows Based"
            elif ttl > 250: os_guess = "Cisco/Network"

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

def get_full_audit(ip, user, password, pre_ping_success=False, pre_hostname=None):
    is_online = pre_ping_success
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    ttl_val = None
    
    # 1. Try ICMP Ping
    if not is_online:
        try:
            # Attempt 1: Standard Ping
            proc = subprocess.run(['ping', param, '1', '-w', '1000', ip], capture_output=True, text=True, timeout=2, creationflags=CREATE_NO_WINDOW)
            stdout = proc.stdout.lower()
            if "ttl=" in stdout or "conteúdo=" in stdout or "bits=" in stdout or "tempo" in stdout or "time" in stdout or "bytes=" in stdout:
                is_online = True
                match = re.search(r"ttl=(\d+)", stdout)
                if match: ttl_val = int(match.group(1))
            else:
                # Attempt 2: Relaxed Ping (2 packets)
                proc = subprocess.run(['ping', param, '2', '-w', '1000', ip], capture_output=True, text=True, timeout=3, creationflags=CREATE_NO_WINDOW)
                stdout = proc.stdout.lower()
                if "ttl=" in stdout or "tempo" in stdout or "bytes=" in stdout:
                     is_online = True
        except: pass

    # 2. Fallback: Try TCP Ports if Ping verification failed
    # (Firewalls often block ICMP but allow services)
    if not is_online:
        common_ports = [9100, 80, 443, 445, 139, 135, 22, 3389]
        for p in common_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex((ip, p)) == 0:
                        is_online = True
                        break
            except: pass

    if not is_online:
         return None

    info = { 
        "ip": ip, "hostname": "N/A", "os": "N/A", "model": "N/A", 
        "status_code": "ONLINE", 
        "user": "N/A", "ram": "N/A", 
        "cpu": "N/A", "uptime": "N/A", "bios": "N/A",
        "shares": [], "disks": [], "nics": [], "services": [], "errors": [],
        "printer_data": None
    }
    
    try: 
        if pre_hostname and pre_hostname != 'N/A' and pre_hostname != '':
            info["hostname"] = pre_hostname
        else:
            try: info["hostname"] = socket.gethostbyaddr(ip)[0]
            except: pass
    except: pass

    # Only attempt WMI if TTL suggests Windows, but proceed to SNMP regardless
    if ttl_val and 120 <= ttl_val <= 130:
        try:
            auth_cmd = f'net use \\\\{ip}\\IPC$ /user:{user} "{password}"'
            auth_res = subprocess.run(auth_cmd, shell=True, capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW)
            
            if auth_res.returncode == 0:
                # WMI/SMB authenticated - valid Windows
                ps_script = resource_path(os.path.join("scripts", "audit_windows.ps1"))
                password_escaped = password.replace("'", "''")
                script_block = f"""& {{
                    $p = ConvertTo-SecureString '{password_escaped}' -AsPlainText -Force;
                    & '{ps_script}' -Ip '{ip}' -User '{user}' -Password $p -TryFallback
                }}"""
                ps_cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script_block]
                audit_proc = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=15, creationflags=CREATE_NO_WINDOW)
                
                if audit_proc.returncode == 0 and audit_proc.stdout.strip():
                    try:
                        audit_data = json.loads(audit_proc.stdout.strip())
                        info.update({
                            "hostname": audit_data.get("hostname", info["hostname"]),
                            "os": audit_data.get("os", "N/A"),
                            "model": audit_data.get("model", "N/A"),
                            "user": audit_data.get("user", "N/A"),
                            "ram": f"{audit_data.get('ramGB')} GB" if audit_data.get("ramGB") != "N/A" else "N/A",
                            "cpu": audit_data.get("cpu", "N/A"),
                            "uptime": audit_data.get("uptime", "N/A"),
                            "bios": audit_data.get("bios", "N/A"),
                            "shares": audit_data.get("shares", []),
                            "disks": audit_data.get("disks", []),
                            "nics": audit_data.get("nics", []),
                            "services": audit_data.get("services", []),
                            "errors": audit_data.get("errors", [])
                        })
                    except json.JSONDecodeError:
                        info["errors"].append("Erro ao processar JSON do PowerShell")
                else:
                    info["errors"].append(f"Script PowerShell falhou (Exit: {audit_proc.returncode})")
                subprocess.run(f"net use \\\\{ip}\\IPC$ /delete /y", shell=True, capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            info["errors"].append(f"Erro na auditoria: {str(e)}")

    mac = DeviceIntelligence.get_mac_address(ip)
    vendor = DeviceIntelligence.get_vendor(mac)
    dtype, icon, conf = DeviceIntelligence.identify_type(ip, ttl_val, info)

    if dtype == "printer":
        p_audit = get_printer_data(ip)
        if p_audit:
            info["printer_data"] = p_audit
            # Enrich core info with SNMP data if available
            if p_audit.get("model") and p_audit.get("model") != "N/A":
                info["model"] = p_audit["model"]
            if p_audit.get("hostname") and p_audit.get("hostname") != "N/A":
                info["hostname"] = p_audit["hostname"]
            if p_audit.get("uptime") and p_audit.get("uptime") != "N/A":
                info["uptime"] = p_audit["uptime"]
            if "serial" in p_audit: info["serial"] = p_audit["serial"]
            if p_audit.get("location"): info["location"] = p_audit["location"] # Optional field support

    return {
        "ip": ip, "hostname": info["hostname"], "device_type": dtype, "icon": icon, "vendor": vendor, "mac": mac or "-",
        "os_detail": info["os"] if info["os"] != "N/A" else f"Baseado em TTL={ttl_val}",
        "user": info["user"], "model": info["model"], "ram": info["ram"], "cpu": info["cpu"], "uptime": info["uptime"],
        "bios": info["bios"], "shares": info["shares"], "disks": info["disks"], 
        "nics": info["nics"], "services": info["services"], "errors": info["errors"],
        "printer_data": info["printer_data"],
        "confidence": conf,
        "last_seen": datetime.now().isoformat()
    }

def save_db(data):
    """Grava/Atualiza dispositivos no SQLite de forma atômica"""
    from database import get_session
    from models import Device
    session = get_session()
    try:
        for item in data:
            device = session.query(Device).filter_by(ip=item['ip']).first()
            if not device:
                device = Device(ip=item['ip'])
                session.add(device)
            
            device.hostname = item.get('hostname', device.hostname)
            device.device_type = item.get('device_type', device.device_type)
            device.icon = item.get('icon', device.icon)
            device.vendor = item.get('vendor', device.vendor)
            device.mac = item.get('mac', device.mac)
            device.os_detail = item.get('os_detail', device.os_detail)
            device.model = item.get('model', device.model)
            device.user = item.get('user', device.user)
            device.ram = item.get('ram', device.ram)
            device.cpu = str(item.get('cpu', device.cpu))
            device.uptime = item.get('uptime', device.uptime)
            device.bios = item.get('bios', device.bios)
            device.shares = item.get('shares', device.shares)
            device.disks = item.get('disks', device.disks)
            device.nics = item.get('nics', device.nics)
            device.services = item.get('services', device.services)
            device.errors = item.get('errors', device.errors)
            device.printer_data = item.get('printer_data', device.printer_data)
            device.confidence = item.get('confidence', device.confidence)
            device.last_seen = datetime.now()
            
        session.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar no SQLite: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def scan_thread(subnet, admin_user="", admin_pass=""):
    """
    Sentinel Engine 2.1 - O motor de scan definitivo.
    Design resiliente para subredes grandes (/22, /23, /24).
    """
    start_time = time.time()
    update_scan_status({
        "running": True,
        "scanned": 0,
        "etr": "Iniciando...",
        "logs": {"msg": "🚀 Sentinel Engine: Matriz de rede inicializada.", "time": time.strftime("%H:%M:%S")},
        "last_results": {"updated": 0, "added": 0, "total_found": 0}
    })
    
    try:
        net = ipaddress.ip_network(subnet, strict=False)
        total_ips = max(1, net.num_addresses - 2)
        update_scan_status({"total": total_ips})
    except: 
        total_ips = 254
        update_scan_status({"total": 254})
            
    try:
        update_scan_status({"etr": "Descobrindo...", "logs": {"msg": f"🛰️ Analisando topologia: {subnet}", "time": time.strftime("%H:%M:%S")}})
        discovered_hosts = []
        
        # --- PHASE 1: POWERSHELL DISCOVERY ---
        try:
            ps_script = resource_path(os.path.join("scripts", "scan_network.ps1"))
            if os.path.exists(ps_script):
                update_scan_status({"logs": {"msg": "📡 Sentinel PS Core: Disparando varredura rápida...", "time": time.strftime("%H:%M:%S")}})
                cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_script, "-Subnet", subnet]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
                try:
                    stdout, stderr = proc.communicate(timeout=180)
                    if stdout and stdout.strip():
                        # Robusteza: extrair o primeiro JSON válido (ignorar lixo)
                        match = re.search(r'\[.*\]', stdout.replace('\n', '').replace('\r', ''))
                        if match:
                            data = json.loads(match.group(0))
                            # Normalizar: PS pode retornar listas aninhadas em alguns casos
                            raw_list = data if isinstance(data, list) else [data]
                            for item in raw_list:
                                if isinstance(item, list): discovered_hosts.extend(item)
                                else: discovered_hosts.append(item)
                            
                            update_scan_status({"logs": {"msg": f"✅ Fase 1 completa: {len(discovered_hosts)} ativos detectados via PS.", "time": time.strftime("%H:%M:%S")}})
                        else:
                            update_scan_status({"logs": {"msg": "⚠️ Falha no sinal JSON do PS Engine.", "time": time.strftime("%H:%M:%S")}})
                    else:
                        update_scan_status({"logs": {"msg": "⚠️ PS Engine retornou silêncio (Rede protegida?).", "time": time.strftime("%H:%M:%S")}})
                except subprocess.TimeoutExpired:
                    proc.kill()
                    update_scan_status({"logs": {"msg": "⏰ Tempo limite do PS excedido (Segmento muito grande).", "time": time.strftime("%H:%M:%S")}})
            else:
                update_scan_status({"logs": {"msg": "🔴 Script Sentinel PS não encontrado.", "time": time.strftime("%H:%M:%S")}})
        except Exception as e:
            logger.error(f"Erro PS: {e}")
            update_scan_status({"logs": {"msg": f"❌ Falha crítica PS: {str(e)}", "time": time.strftime("%H:%M:%S")}})

        # --- PHASE 1.5: PYTHON FALLBACK ---
        if not discovered_hosts:
            update_scan_status({"logs": {"msg": "🛠️ Ativando Fallback Engine (Ping Sweep Nativo)...", "time": time.strftime("%H:%M:%S")}})
            def quick_ping(ip):
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                try:
                    res = subprocess.run(['ping', param, '1', '-w', '200', str(ip)], capture_output=True, creationflags=CREATE_NO_WINDOW)
                    if res.returncode == 0: return {"IP": str(ip), "Status": "Online", "Hostname": ""}
                except: pass
                return None

            try:
                ips_to_ping = list(net.hosts())[:1024] # Safety cap
                with ThreadPoolExecutor(max_workers=64) as discovery_executor:
                    discovered_hosts = [h for h in discovery_executor.map(quick_ping, ips_to_ping) if h]
                update_scan_status({"logs": {"msg": f"✅ Fallback finalizado: {len(discovered_hosts)} ativos encontrados.", "time": time.strftime("%H:%M:%S")}})
            except Exception as e:
                update_scan_status({"logs": {"msg": f"❌ Erro no Fallback: {str(e)}", "time": time.strftime("%H:%M:%S")}})

        if not discovered_hosts:
            update_scan_status({
                "logs": {"msg": "🔍 Fim da varredura: Nenhum dispositivo respondeu.", "time": time.strftime("%H:%M:%S")},
                "total": 1, "scanned": 1, "etr": "Concluído"
            })
            time.sleep(10)
            return
            
        # --- PHASE 2: AUDIT ---
        total_discovered = len(discovered_hosts)
        
        # Pre-fetch existing IPs to determine NEW/UPDATED status quickly
        from database import get_session
        from models import Device
        db_session = get_session()
        existing_ips = {d.ip for d in db_session.query(Device.ip).all()}
        db_session.close()

        update_scan_status({
            "total": total_discovered,
            "scanned": 0,
            "logs": {"msg": f"🔍 Iniciando auditoria profunda em {total_discovered} alvos...", "time": time.strftime("%H:%M:%S")}
        })
        
        audit_executor = ThreadPoolExecutor(max_workers=8)
        futures = []

        def audit_worker(host_data):
            ip = host_data.get('IP') or host_data.get('ip')
            hostname = host_data.get('Hostname') or host_data.get('hostname') or ''
            try:
                return get_full_audit(ip, admin_user, admin_pass, pre_ping_success=True, pre_hostname=hostname)
            except Exception as e:
                logger.error(f"Audit Fail {ip}: {e}")
                return None

        for h in discovered_hosts:
            futures.append(audit_executor.submit(audit_worker, h))
            
        updated, added, completed = 0, 0, 0
        
        for f in futures:
            try:
                r = f.result(timeout=60) # Cada host tem 1 min p/ responder auditoria
                completed += 1
                if r:
                    with results_lock:
                        # Mark as NEW or UPDATED based on pre-fetched state
                        r['scan_type'] = 'new' if r['ip'] not in existing_ips else 'updated'

                        found_idx = next((i for i, x in enumerate(scan_status["results"]) if x['ip'] == r['ip']), -1)
                        if found_idx >= 0:
                            scan_status["results"][found_idx] = r
                            updated += 1
                        else:
                            scan_status["results"].append(r)
                            added += 1
                        
                        update_scan_status({"logs": {"msg": f"Auditado: {r['ip']} ({r['hostname']})", "time": time.strftime("%H:%M:%S")}})
                        save_db([r]) 

                # Update progress
                elapsed = time.time() - start_time
                rate = elapsed / completed if completed > 0 else 1
                rem = int((total_discovered - completed) * rate)
                update_scan_status({
                    "scanned": completed,
                    "etr": f"{rem}s",
                    "last_results": {"updated": updated, "added": added, "total_found": updated + added}
                })
            except Exception as e:
                completed += 1
                logger.error(f"Worker Error: {e}")

        audit_executor.shutdown(wait=False)
        update_scan_status({
            "logs": {"msg": f"📢 SCAN CONCLUÍDO: {added} novos, {updated} atualizados.", "time": time.strftime("%H:%M:%S")},
            "etr": "Concluído",
            "scanned": total_discovered
        })
        time.sleep(15) 

    except Exception as e:
        logger.exception("Engine Crash")
        update_scan_status({"logs": {"msg": f"🛑 ERRO NO MOTOR: {str(e)}", "time": time.strftime("%H:%M:%S")}})
        time.sleep(10)
    finally:
        update_scan_status({
            "logs": {"msg": "💤 Motor Sentinel em espera.", "time": time.strftime("%H:%M:%S")},
            "running": False,
            "etr": "Portal Sentinel em repouso..."
        })
def rdp_gateway_loop():
    logger.info("[RDP GATEWAY] Iniciando serviço auxiliar Node.js...")
    try:
        subprocess.Popen(["node", "rdp-gateway.js"], shell=True, creationflags=0x08000000 if platform.system() == 'Windows' else 0)
    except Exception as e:
        logger.error(f"[RDP GATEWAY] Falha ao iniciar gateway: {e}")
