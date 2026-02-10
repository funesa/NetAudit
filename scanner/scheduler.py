import time
import threading
from shared_state import scan_status
from scanner.engine import scan_thread
from utils import safe_json_load, safe_json_save, logger, get_data_path

SCHEDULE_FILE = get_data_path("scan_schedule.json")

def load_schedule():
    default_config = {
        "enabled": False,
        "interval": 60,
        "unit": "minutes",
        "last_run": None,
        "subnet": ""
    }
    return safe_json_load(SCHEDULE_FILE, default=default_config)

def save_schedule(config):
    return safe_json_save(SCHEDULE_FILE, config)

schedule_config = load_schedule()

def scheduler_loop():
    """Thread em background que executa scans automáticos baseado na configuração"""
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
                            logger.info(f"[SCHEDULER] Iniciando scan automático para {subnet}")
                            # Get credentials from current settings
                            from utils import load_general_settings
                            import os
                            settings = load_general_settings()
                            ad_config = settings.get('ad_config', {})
                            admin_user = ad_config.get('username') or os.environ.get("NETAUDIT_SCAN_USER", "")
                            admin_pass = ad_config.get('password') or os.environ.get("NETAUDIT_SCAN_PASS", "")
                            
                            threading.Thread(target=scan_thread, args=(subnet, admin_user, admin_pass), daemon=True).start()
                            schedule_config["last_run"] = now
                            save_schedule(schedule_config)
        except Exception as e:
            logger.error(f"[SCHEDULER ERROR] {e}")
        
        time.sleep(30)
