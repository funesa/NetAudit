from flask import Blueprint, render_template, request, jsonify
from core.decorators import login_required
from license_manager import lic_manager

license_bp = Blueprint('license_management', __name__)

@license_bp.route('/license')
@login_required
def license_page():
    return render_template('license.html', hwid=lic_manager.get_hwid())

@license_bp.route('/api/license/activate', methods=['POST'])
@login_required
def api_activate_license():
    data = request.json
    key = data.get('key')
    if not key: return jsonify({'success': False, 'message': 'Chave vazia'})
        
    valid, user_data = lic_manager.validate_license(key)
    if valid:
        lic_manager.save_license(key)
        return jsonify({'success': True, 'message': f'Ativada para {user_data.get("customer")}!'})
    return jsonify({'success': False, 'message': user_data})
@license_bp.route('/api/license/info')
@login_required
def api_license_info():
    return jsonify({
        'hwid': lic_manager.get_hwid(),
        'is_premium': lic_manager.is_premium(),
        'customer': lic_manager.get_current_license().get('customer', 'Trial') if lic_manager.is_premium() else 'Trial',
        'trial_days_left': lic_manager.get_trial_status()
    })
