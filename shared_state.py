import threading
import logging

logger = logging.getLogger('NetAudit.State')

# Objeto global para compartilhar o estado do scan entre app.py e ai_actions.py
scan_status = {
    "running": False,
    "results": [],
    "progress": 0,
    "total": 0,
    "scanned": 0,
    "etr": "Portal Sentinel em repouso...",
    "last_results": {"updated": 0, "added": 0, "total_found": 0},
    "logs": []
}

scan_lock = threading.Lock()
results_lock = threading.Lock()

def update_scan_status(updates):
    """Atualiza o estado global de forma segura e loga mudanças críticas"""
    with scan_lock:
        for k, v in updates.items():
            if k == "logs" and isinstance(v, list):
                # Se for uma lista completa, substitui (usado no reset)
                scan_status[k] = v
            elif k == "logs":
                # Se for um único log (item), adiciona
                scan_status["logs"].append(v)
                if len(scan_status["logs"]) > 100:
                    scan_status["logs"] = scan_status["logs"][-100:]
            else:
                scan_status[k] = v
        
        if "etr" in updates or "running" in updates:
            logger.debug(f"Status update: running={scan_status['running']}, etr={scan_status['etr']}")
