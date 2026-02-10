import platform
import subprocess

def format_user_card(user):
    username = user.get('SamAccountName')
    display = user.get('DisplayName')
    return f"""<div style="background:rgba(167, 139, 250, 0.05); padding:15px; border-radius:12px; border:1px solid rgba(167, 139, 250, 0.2); display:flex; align-items:center; gap:15px; margin-bottom:10px;">
        <div style="width:45px; height:45px; background:rgba(167, 139, 250, 0.2); border-radius:50%; display:flex; align-items:center; justify-content:center; color:#a78bfa; font-size:1.2rem;"><i class="ph-fill ph-user"></i></div>
        <div style="flex:1;">
            <div style="color:white; font-weight:bold; font-size:1rem;">{display}</div>
            <div style="color:#a78bfa; font-size:0.8rem; font-family:monospace;">{username}</div>
        </div></div>"""

def format_asset_card(asset):
    icon = asset.get('icon', 'ph-desktop')
    status_color = "#10b981" if asset.get('status_code', 'ONLINE') == 'ONLINE' else "#ef4444"
    return f"""<div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:10px; border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; gap:12px; margin-bottom:8px;">
        <div style="width:40px; height:40px; background:rgba(59,130,246,0.2); border-radius:8px; display:flex; align-items:center; justify-content:center; color:#60a5fa;"><i class="ph-fill {icon}"></i></div>
        <div style="flex:1;">
            <div style="display:flex; justify-content:space-between;"><strong>{asset.get('hostname', 'Unknown')}</strong><span style="color:{status_color}; font-size:0.8rem;">{asset.get('ip')}</span></div>
            <div style="color:#94a3b8; font-size:0.8rem;">{asset.get('os_detail', 'N/A')} • {asset.get('user', 'N/A')}</div>
        </div></div>"""

def ping_ip(ip):
    try:
        cmd = ['ping', '-n' if platform.system().lower() == 'windows' else '-c', '1', '-w' if platform.system().lower() == 'windows' else '-W', '500', ip]
        return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000 if platform.system().lower() == 'windows' else 0) == 0
    except: return False

def load_scan_data():
    try:
        from shared_state import scan_status
        results = scan_status.get("results", [])
        if not results:
            from database import load_all_devices
            results = load_all_devices()
            scan_status["results"] = results
        return results
    except Exception as e:
        print(f"Erro ao carregar scan data: {e}")
        return []
