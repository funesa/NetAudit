from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_session
from models import User
from security import decrypt_value, encrypt_value
from ad_helper import authenticate_ad
from utils import logger, load_general_settings
from core.decorators import login_required
from core.permissions import require_permission

auth_bp = Blueprint('auth', __name__)

def check_setup():
    session_db = get_session()
    try:
        return session_db.query(User).count() > 0
    except: return False
    finally: session_db.close()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Legacy/Template Route
    if not check_setup():
        return redirect(url_for('auth.setup_page'))
        
    if request.method == 'GET':
        if 'username' in session:
            return redirect(url_for('dashboard.home'))
        return render_template('login.html')
    
    return process_login(request.json)

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    # Dedicated API Route for React
    return process_login(request.json)

def process_login(data):
    if not data:
        return jsonify({'success': False, 'message': 'Dados inválidos'}), 400

    username = data.get('username')
    password = data.get('password')
    
    logger.info(f"[AUTH] Tentativa de login para: '{username}'")
    
    session_db = get_session()
    try:
        # Tenta buscar exato e lowercase
        user = session_db.query(User).filter(User.username.ilike(username)).first()
        if user:
            logger.info(f"[AUTH] Usuário '{user.username}' encontrado no banco local")
            decrypted_pass = decrypt_value(user.password)
            if decrypted_pass == password:
                logger.info(f"[AUTH] Login local bem-sucedido: '{username}'")
                session['username'] = user.username # Normaliza sessão para o nome real do DB
                session['role'] = user.role or 'admin'
                session['is_master'] = (user.id == 1)
                # Garante que as permissões sejam um dicionário (SQLite pode retornar string)
                import json
                perms_raw = user.permissions
                if isinstance(perms_raw, str):
                    try: perms_raw = json.loads(perms_raw)
                    except: perms_raw = {}
                
                session['permissions'] = perms_raw if (perms_raw and isinstance(perms_raw, dict) and len(perms_raw) > 0) else {'view_all': True}
                session.modified = True
                session.permanent = True
                return jsonify({
                    'success': True, 
                    'permissions': session['permissions'], 
                    'is_master': session['is_master']
                })
            else:
                logger.warning(f"[AUTH] Senha incorreta para: '{username}'")
        else:
            logger.info(f"[AUTH] Usuário '{username}' não encontrado no banco local")
    except Exception as e:
        logger.error(f"[AUTH] Erro ao consultar banco local: {e}")
    finally:
        session_db.close()
    
    settings = load_general_settings()
    if settings.get('ad_enabled', True):
        logger.info(f"[AUTH] Tentando autenticação AD para: '{username}'")
        if authenticate_ad(username, password):
            session['username'] = username
            session['role'] = 'user'
            session['is_master'] = False
            session['permissions'] = {
                'view_all': True, 
                'ad_view': True, 
                'helpdesk_view': True
            }
            logger.info(f"[AUTH] Login AD bem-sucedido: '{username}'")
            return jsonify({
                'success': True, 
                'ad': True, 
                'permissions': session['permissions'],
                'is_master': False
            })
    
    logger.warning(f"[AUTH] Falha de autenticação para: '{username}'")
    return jsonify({'success': False, 'message': 'Credenciais inválidas.'})

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def get_me():
    """Retorna informações atualizadas do usuário logado"""
    username = session.get('username')
    session_db = get_session()
    try:
        user = session_db.query(User).filter(User.username.ilike(username)).first()
        if user:
            import json
            perms = user.permissions
            if isinstance(perms, str):
                try: perms = json.loads(perms)
                except: perms = {}
            
            if not perms or not isinstance(perms, dict):
                perms = {'view_all': True}
            
            # Atualiza sessão com dados reais do DB
            session['permissions'] = perms
            session['is_master'] = (user.id == 1)
            session.modified = True
            
            return jsonify({
                'username': user.username,
                'role': user.role,
                'is_master': session['is_master'],
                'permissions': perms
            })
    except Exception as e:
        logger.error(f"Erro em get_me: {e}")
    finally:
        session_db.close()
        
    return jsonify({
        'username': session.get('username'),
        'role': session.get('role'),
        'is_master': session.get('is_master', False),
        'permissions': session.get('permissions', {'view_all': True})
    })

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup_page():
    if check_setup():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        data = request.json
        user_name = data.get('username')
        pw = data.get('password')
        if user_name and pw:
            session_db = get_session()
            try:
                new_user = User(
                    username=user_name,
                    password=encrypt_value(pw),
                    role="admin",
                    full_name="Administrador Master"
                )
                session_db.add(new_user)
                session_db.commit()
                return jsonify({"success": True})
            except Exception as e:
                session_db.rollback()
                return jsonify({"success": False, "message": str(e)})
            finally:
                session_db.close()
    return render_template('setup.html')

@auth_bp.route('/settings/users')
@login_required
def system_users_page():
    """Página de gerenciamento de usuários do sistema"""
    return render_template('system_users.html')

@auth_bp.route('/api/system/users', methods=['GET'])
@login_required
@require_permission('manage_system_users')
def list_users():
    """Lista todos os usuários do sistema"""
    session_db = get_session()
    try:
        users = session_db.query(User).all()
        users_data = []
        for user in users:
            users_data.append({
                'username': user.username,
                'role': user.role or 'user',
                'full_name': user.full_name or '',
                'is_active': user.is_active if hasattr(user, 'is_active') else True,
                'is_master': (user.id == 1),
                'permissions': user.permissions or {
                    'view_all': True
                }
            })
        return jsonify(users_data)
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        session_db.close()

@auth_bp.route('/api/system/users', methods=['POST'])
@login_required
@require_permission('manage_system_users')
def create_user():
    """Cria um novo usuário"""
    from core.decorators import admin_required_check
    if not admin_required_check():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    is_active = data.get('is_active', True)
    permissions = data.get('permissions', {'view_all': True})
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username e senha são obrigatórios'}), 400
    
    session_db = get_session()
    try:
        # Verifica se usuário já existe
        existing = session_db.query(User).filter_by(username=username).first()
        if existing:
            return jsonify({'success': False, 'message': 'Usuário já existe'}), 400
        
        new_user = User(
            username=username,
            password=encrypt_value(password),
            role=role,
            full_name=data.get('full_name', username),
            permissions=permissions
        )
        
        # Adiciona is_active se o modelo suportar
        if hasattr(User, 'is_active'):
            new_user.is_active = is_active
        
        session_db.add(new_user)
        session_db.commit()
        return jsonify({'success': True, 'message': 'Usuário criado com sucesso'})
    except Exception as e:
        session_db.rollback()
        logger.error(f"Erro ao criar usuário: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        session_db.close()

@auth_bp.route('/api/system/users/<username>', methods=['PUT'])
@login_required
@require_permission('manage_system_users')
def update_user(username):
    """Atualiza um usuário existente"""
    from core.decorators import admin_required_check
    if not admin_required_check():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    data = request.json
    session_db = get_session()
    try:
        user = session_db.query(User).filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        # Não permite alterar o usuário master (ID 1)
        if user.id == 1 and data.get('password'):
            return jsonify({'success': False, 'message': 'Não é possível alterar a senha do usuário master por aqui'}), 403
        
        # Atualiza campos
        if data.get('password'):
            user.password = encrypt_value(data['password'])
        if 'role' in data and user.id != 1:  # Não altera role do master
            user.role = data['role']
        if 'is_active' in data:
            if hasattr(user, 'is_active'):
                user.is_active = data['is_active']
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'permissions' in data:
            user.permissions = data['permissions']
        
        session_db.commit()
        return jsonify({'success': True, 'message': 'Usuário atualizado com sucesso'})
    except Exception as e:
        session_db.rollback()
        logger.error(f"Erro ao atualizar usuário: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        session_db.close()

@auth_bp.route('/api/system/users/<username>', methods=['DELETE'])
@login_required
@require_permission('manage_system_users')
def delete_user(username):
    """Deleta um usuário"""
    from core.decorators import admin_required_check
    if not admin_required_check():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    session_db = get_session()
    try:
        user = session_db.query(User).filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        # Não permite deletar o usuário master
        if user.id == 1:
            return jsonify({'success': False, 'message': 'Não é possível deletar o usuário master'}), 403
        
        # Não permite deletar a si mesmo
        if username == session.get('username'):
            return jsonify({'success': False, 'message': 'Você não pode deletar sua própria conta'}), 403
        
        session_db.delete(user)
        session_db.commit()
        return jsonify({'success': True, 'message': 'Usuário deletado com sucesso'})
    except Exception as e:
        session_db.rollback()
        logger.error(f"Erro ao deletar usuário: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        session_db.close()
