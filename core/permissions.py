from functools import wraps
from flask import session, jsonify, abort

def has_permission(permission):
    """
    Verifica se o usuário logado tem uma permissão específica.
    """
    if 'username' not in session:
        return False
        
    # Master user sempre tem todas as permissões
    if session.get('is_master'):
        return True
        
    permissions = session.get('permissions', {})
    
    # Segurança extra: garante que seja um dict (pode vir como string do SQLite)
    if isinstance(permissions, str):
        import json
        try: permissions = json.loads(permissions)
        except: permissions = {}
    
    # Se tiver 'all': true, tem permissão total
    if permissions.get('all'):
        return True
        
    return permissions.get(permission, False)

def require_permission(permission):
    """
    Decorator para proteger rotas do Flask com permissões granulares.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_permission(permission):
                return jsonify({
                    'success': False, 
                    'message': f'Acesso negado: permissão "{permission}" necessária.'
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Lista de permissões sugeridas:
# - view_all: Ver dashboards e inventário
# - run_scan: Iniciar varreduras de rede
# - manage_ad: Resetar senhas, desbloquear, criar usuários AD
# - manage_system_users: Criar/Editar usuários do NetAudit
# - manage_settings: Alterar configurações gerais, licença
# - view_logs: Ver logs de auditoria e segurança
