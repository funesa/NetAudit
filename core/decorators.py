from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from license_manager import lic_manager
from utils import load_general_settings, logger

def login_required(f):
    """Decorator para proteger rotas que requerem autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Sessão expirada. Faça login novamente.'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def premium_required(f):
    """Decorator para recursos que exigem licença Premium ou Trial"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not lic_manager.has_pro_access():
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Recurso Premium necessário.'}), 403
            return redirect(url_for('license_management.license_page'))
        return f(*args, **kwargs)
    return decorated_function

def ad_required(f):
    """Decorator para recursos do Active Directory"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        settings = load_general_settings()
        user_perms = session.get('permissions', {})
        
        # Acesso PRO Requerido
        if not lic_manager.has_pro_access():
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso ao AD requer licença Premium ou Trial ativo.'}), 403
            return redirect(url_for('license_management.license_page'))

        # Verifica se o AD está habilitado globalmente E para o usuário
        if not settings.get('ad_enabled', True) or not user_perms.get('ad', True):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso ao AD não permitido ou desativado.'}), 403
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator para acesso administrativo"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Privilégios de administrador requeridos.'}), 403
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def tickets_required(f):
    """Decorator para acesso ao Helpdesk (GLPI)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        settings = load_general_settings()
        user_perms = session.get('permissions', {})
        
        # Acesso PRO Requerido
        if not lic_manager.has_pro_access():
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso ao Helpdesk requer licença Premium ou Trial ativo.'}), 403
            return redirect(url_for('license_management.license_page'))

        # Verifica se o Helpdesk está habilitado globalmente E para o usuário
        if not settings.get('tickets_enabled', True) or not user_perms.get('helpdesk', True):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso ao Helpdesk não permitido ou desativado.'}), 403
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required_check():
    """Helper function para verificar se o usuário atual é admin (sem decorator)"""
    return session.get('role') == 'admin'

