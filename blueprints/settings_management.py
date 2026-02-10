from flask import Blueprint, request, jsonify
from core.decorators import login_required, admin_required
from utils import load_general_settings, save_general_settings, logger
from cache_helper import clear_cache
import os

settings_bp = Blueprint('settings_management', __name__)

@settings_bp.route('/api/settings/general', methods=['GET', 'POST'])
@login_required
@admin_required
def general_settings_route():
    if request.method == 'POST':
        data = request.json
        current = load_general_settings()
        
        if 'ai_enabled' in data: current['ai_enabled'] = bool(data['ai_enabled'])
        if 'ad_enabled' in data:
            val = bool(data['ad_enabled'])
            if current.get('ad_enabled') and not val:
                # Cleanup AD data
                for f in ['ad_config.json', 'ad_last_connection.json', 'ad_cache.json']:
                    if os.path.exists(f): os.remove(f)
                clear_cache()
            current['ad_enabled'] = val
            
        if 'tickets_enabled' in data:
            val = bool(data['tickets_enabled'])
            if current.get('tickets_enabled') and not val:
                if os.path.exists('glpi_config.json'): os.remove('glpi_config.json')
            current['tickets_enabled'] = val

        if 'dashboard_refresh_interval' in data:
            try: current['dashboard_refresh_interval'] = int(data['dashboard_refresh_interval'])
            except: pass
        
        save_general_settings(current)
        return jsonify({"status": "success", "settings": current})
    
    return jsonify(load_general_settings())
