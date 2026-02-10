from flask import Blueprint, render_template, request, jsonify
from core.decorators import login_required, ad_required, premium_required
from core.permissions import require_permission
from ad_helper import (
    get_ad_users, reset_ad_password, unlock_user_account, 
    toggle_user_status, get_ad_storage, get_failed_logins
)
from utils import logger

ad_bp = Blueprint('ad_management', __name__)

@ad_bp.route('/ad-users')
@login_required
@ad_required
@premium_required
@require_permission('view_all')
def ad_users_page():
    return render_template('ad_users.html')

@ad_bp.route('/api/ad/users')
@login_required
@ad_required
@require_permission('view_all')
def api_ad_users():
    users = get_ad_users()
    response = jsonify(users)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@ad_bp.route('/api/ad/reset-password', methods=['POST'])
@login_required
@ad_required
@require_permission('manage_ad')
def api_reset_password():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    success, message = reset_ad_password(username, password)
    return jsonify({'success': success, 'message': message})

@ad_bp.route('/ad-config')
@login_required
@ad_required
@require_permission('manage_settings')
def ad_config_page():
    return render_template('ad_config.html')

@ad_bp.route('/ad-shares')
@login_required
@ad_required
def ad_shares_page():
    return render_template('ad_shares.html')

@ad_bp.route('/api/ad/shares')
@login_required
@ad_required
@require_permission('view_all')
def api_ad_shares():
    disks = get_ad_storage()
    return jsonify(disks)

@ad_bp.route('/security')
@login_required
@ad_required
@require_permission('view_all')
def security_page():
    return render_template('security.html')

@ad_bp.route('/api/security/failed-logins')
@login_required
def api_failed_logins():
    """API para retornar logins falhados (usado pelo dashboard)"""
    try:
        # Verifica se AD está habilitado
        from utils import load_general_settings
        settings = load_general_settings()
        
        if not settings.get('ad_enabled', True):
            # AD desabilitado, retorna vazio
            return jsonify({
                'success': True,
                'count': 0,
                'logins': []
            })
        
        hours = request.args.get('hours', 24, type=int)
        logins = get_failed_logins(hours)
        return jsonify({
            'success': True,
            'count': len(logins) if logins else 0,
            'logins': logins or []
        })
    except Exception as e:
        logger.error(f"Erro ao buscar logins falhados: {e}")
        return jsonify({
            'success': True,  # Retorna success=True para não quebrar o dashboard
            'count': 0,
            'logins': [],
            'error': str(e)
        })
@ad_bp.route('/api/ad/status')
@login_required
def api_ad_status():
    from ad_helper import load_ad_config, get_last_ad_connection
    from utils import load_general_settings
    settings = load_general_settings()
    config = load_ad_config()
    last_conn = get_last_ad_connection()
    
    return jsonify({
        'configured': bool(config),
        'enabled': settings.get('ad_enabled', True),
        'lastConnection': last_conn,
        'config': {
            'server': config.get('server', ''),
            'domain': config.get('domain', ''),
            'baseDN': config.get('baseDN', ''),
            'adminUser': config.get('adminUser', '')
        } if config else None
    })

@ad_bp.route('/api/ad/save-config', methods=['POST'])
@login_required
@require_permission('manage_settings')
def api_save_ad_config():
    from security import save_encrypted_json
    from cache_helper import clear_cache
    from ad_helper import load_ad_config
    data = request.json
    print(f"DEBUG: Recebendo solicitação de salvamento AD")
    
    try:
        # Carrega config atual para não perder a senha se não for enviada
        current_config = load_ad_config()
        
        config = {
            'server': data.get('server'),
            'domain': data.get('domain'),
            'baseDN': data.get('baseDN'),
            'adminUser': data.get('adminUser'),
            'adminPass': data.get('adminPass') or current_config.get('adminPass', '')
        }
        
        save_encrypted_json('ad_config.json', config, fields_to_encrypt=['adminPass'])
        clear_cache()
        print("DEBUG: Config AD salva com sucesso (com preservação de senha se necessário)")
        return jsonify({'success': True, 'message': 'Configuração salva com sucesso'})
    except Exception as e:
        print(f"DEBUG ERROR: Falha ao salvar config AD: {e}")
        return jsonify({'success': False, 'message': f'Erro ao salvar: {str(e)}'})

@ad_bp.route('/api/ad/test-connection', methods=['POST'])
@login_required
def api_test_ad_connection():
    from ad_helper import record_ad_success, load_ad_config, test_ad_connection_native
    data = request.json
    server_addr = data.get('server')
    domain = data.get('domain')
    admin_user = data.get('adminUser')
    admin_pass = data.get('adminPass')
    
    # Busca config atual para fallback de senha
    current_config = load_ad_config()
    if not admin_pass:
        admin_pass = current_config.get('adminPass', '')
    
    print(f"DEBUG: Testando conexão AD em {server_addr} via PowerShell (Nativo)")
    
    if not all([server_addr, domain, admin_user, admin_pass]):
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios para o teste. Se você não digitou a senha, certifique-se de que já salvou uma anteriormente.'})

    # Usamos o método nativo via PowerShell que é muito mais compatível em ambientes Windows AD
    success, message = test_ad_connection_native(server_addr, domain, admin_user, admin_pass)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        # Se falhar o nativo, tentamos ldap3 como último recurso (raro funcionar se o nativo falhar, mas ok)
        try:
            from ldap3 import Server, Connection, ALL, SIMPLE
            user_dn = f"{admin_user}@{domain}"
            server = Server(server_addr, get_info=ALL, connect_timeout=5)
            conn = Connection(server, user=user_dn, password=admin_pass, authentication=SIMPLE)
            if conn.bind():
                conn.unbind()
                record_ad_success()
                return jsonify({'success': True, 'message': 'Conexão estabelecida via ldap3 (fallback).'})
        except: pass
        
        return jsonify({'success': False, 'message': message})
