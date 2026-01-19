# Active Directory Helper Functions
from ldap3 import Tls, Server, Connection, ALL, NTLM, MODIFY_REPLACE, SIMPLE
from ldap3.core.exceptions import LDAPException
from functools import wraps
from flask import session, redirect, url_for
from cache_helper import cache_result
from utils import load_general_settings, resource_path
import json
import os
import ssl

# Active Directory Configuration - Sempre carregada dinamicamente para permitir reset total
def get_current_config():
    return load_ad_config() or {}

# MODO DE TESTE - Desabilita AD temporariamente
TEST_MODE = False
TEST_USERS = {}

def load_ad_config(username=None):
    """Carrega configuração do AD (Prioriza credenciais individuais do usuário)"""
    from security import load_encrypted_json
    from flask import session
    
    try:
        target_user = username or session.get('username')
    except:
        target_user = username or "system"
    
    # 1. Tenta carregar credenciais individuais do users.json
    if target_user:
        users = load_encrypted_json("users.json", fields_to_decrypt=["password"], default=[])
        for u in users:
            if u['username'] == target_user and 'credentials' in u and 'ad' in u['credentials']:
                return u['credentials']['ad']
    
    # 2. Fallback para configuração global
    return load_encrypted_json("ad_config.json", fields_to_decrypt=["adminPass"])

def record_ad_success():
    """Registra o timestamp da última conexão bem-sucedida"""
    try:
        from datetime import datetime
        data = {"last_success": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
        with open('ad_last_connection.json', 'w') as f:
            json.dump(data, f)
    except:
        pass

def get_last_ad_connection():
    """Retorna o timestamp da última conexão bem-sucedida"""
    if os.path.exists('ad_last_connection.json'):
        try:
            with open('ad_last_connection.json', 'r') as f:
                return json.load(f).get("last_success", "Nunca")
        except:
            pass
    return "Nunca"

def authenticate_ad(username, password):
    """Autentica usuário no Active Directory"""
    # MODO DE TESTE
    if TEST_MODE:
        return TEST_USERS.get(username) == password
    
    # MODO PRODUÇÃO (AD Real)
    config = load_ad_config()
    if not config:
        return False
    
    try:
        user_dn = f"{username}@{config['domain']}"
        server = Server(config['server'], get_info=ALL)
        conn = Connection(server, user=user_dn, password=password, authentication=SIMPLE)
        
        if conn.bind():
            conn.unbind()
            record_ad_success()
            return True
        return False
    except LDAPException as e:
        print(f"AD Auth Error: {e}")
        return False

def get_ad_users():
    """Lista todos os usuários do AD (Failsafe: Verifica status antes do cache)"""
    settings = load_general_settings()
    if not settings.get('ad_enabled', True):
        return []
    return _get_ad_users_impl()

@cache_result(timeout_minutes=5)
def _get_ad_users_impl():
    """Implementação real da busca de usuários"""
    # Se não houver configuração salva (reset), não buscar nada.
    if not os.path.exists('ad_config.json'):
        return []
    
    import subprocess
    script_path = resource_path(os.path.join("scripts", "get_ad_users.ps1"))
    if not os.path.exists(script_path):
        print("Script get_ad_users.ps1 não encontrado.")
        return []

    try:
        config = load_ad_config()
        # Adiciona parâmetros de credenciais se configurados
        if config:
            admin_user = config.get('adminUser', '')
            admin_pass = config.get('adminPass', '').replace("'", "''")
            server = config.get('server', '')
            domain = config.get('domain', '')
            baseDN = config.get('baseDN', '')

            # Construímos o comando usando -Command para converter o adminPass em SecureString
            script_block = f"& {{ $p = ConvertTo-SecureString '{admin_pass}' -AsPlainText -Force; & '{script_path}'"
            if server: script_block += f" -Server '{server}'"
            if domain: script_block += f" -Domain '{domain}'"
            if baseDN: script_block += f" -BaseDN '{baseDN}'"
            if admin_user: script_block += f" -User '{admin_user}'"
            if admin_pass: script_block += f" -Password $p"
            script_block += " }"
            
            cmd = ["powershell", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script_block]
        else:
            cmd = ["powershell", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path]
        
        # Cria o processo forçando encoding de saída UTF-8 para não quebrar acentos
        # CREATE_NO_WINDOW = 0x08000000 (esconde a janela do PowerShell)
        import sys
        if sys.platform == 'win32':
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', creationflags=CREATE_NO_WINDOW)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            print(f"Erro executando Script Users: {result.stderr}")
            # Fallback para array vazio para não quebrar UI
            return []
        
        # O script retorna o JSON direto na saída padrão
        output = result.stdout.strip()
        if not output: return []
        
        try:
            users = json.loads(output)
            
            # --- CRUZAMENTO DE DADOS: AD vs SCAN (scan_history.json) ---
            # Carrega histórico de scan para saber onde o usuário está logado
            scan_file = "scan_history.json"
            logged_map = {} # user_lower -> [ {hostname, ip, date} ]
            
            if os.path.exists(scan_file):
                try:
                    with open(scan_file, 'r', encoding='utf-8') as f:
                        scan_data = json.load(f)
                        # Suporte a lista ou dict (legacy)
                        scan_list = scan_data if isinstance(scan_data, list) else list(scan_data.values())
                        
                        for device in scan_list:
                            # Verifica se tem usuário logado detectado no scan
                            raw_user = device.get("user", "N/A")
                            if raw_user and raw_user not in ["N/A", "", "Unknown"]:
                                # Normaliza: DOMAIN\user -> user
                                clean_user = raw_user.split('\\')[-1].lower()
                                
                                if clean_user not in logged_map: logged_map[clean_user] = []
                                logged_map[clean_user].append({
                                    "hostname": device.get("hostname", "N/A"),
                                    "ip": device.get("ip", "N/A"),
                                    "os": device.get("os", "N/A")
                                })
                except Exception as e_scan:
                    print(f"Erro cruzando dados de scan: {e_scan}")

            # Injeta dados de login nos objetos de usuário do AD
            for u in users:
                u_clean = u.get("username", "").lower()
                if u_clean in logged_map:
                    # Adiciona lista de máquinas onde este usuário foi visto
                    u["logged_machines"] = logged_map[u_clean]
                    # Para exibição rápida (primeira máquina encontrada)
                    first_mach = logged_map[u_clean][0]
                    u["last_machine"] = f"{first_mach['hostname']} ({first_mach['ip']})"
                else:
                    u["logged_machines"] = []
                    u["last_machine"] = "N/A"

            record_ad_success()
            return users
        except json.JSONDecodeError as json_err:
            print(f"Erro decodificando JSON do PowerShell: {json_err}. Output raw: {output[:100]}...")
            return []

    except Exception as e:
        print(f"Erro ao buscar usuários via PS: {e}")
        return []
def reset_ad_password(username, new_password):
    """
    Reseta a senha de um usuário no AD chamando um script PowerShell externo.
    Isso contorna problemas de SSL/TLS da biblioteca ldap3.
    """
    config = load_ad_config()
    if not config: return False, "AD Off"
    
    import subprocess
    import os

    try:
        # Caminho absoluto para o script
        script_path = resource_path(os.path.join("scripts", "reset_password.ps1"))
        
        # Escapamos aspas simples nas senhas
        admin_pass_escaped = config['adminPass'].replace("'", "''")
        new_pass_escaped = new_password.replace("'", "''")
        
        # Construímos comando usando -Command para converter senhas em SecureString
        script_block = f"""& {{
            $adminPass = ConvertTo-SecureString '{admin_pass_escaped}' -AsPlainText -Force;
            $newPass = ConvertTo-SecureString '{new_pass_escaped}' -AsPlainText -Force;
            & '{script_path}' -Server '{config['server']}' -Domain '{config['domain']}' -AdminUser '{config['adminUser']}' -AdminPass $adminPass -TargetUsername '{username}' -NewPassword '{new_password}'
        }}"""
        
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-Command", script_block]
        
        # Tenta executar com UTF-8 explícito primeiro
        # CREATE_NO_WINDOW esconde a janela do PowerShell
        CREATE_NO_WINDOW = 0x08000000
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=15, creationflags=CREATE_NO_WINDOW)
        except UnicodeDecodeError:
            # Fallback para cp1252 se utf-8 falhar (comum em Windows legado)
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='cp1252', timeout=15, creationflags=CREATE_NO_WINDOW)
        
        output = result.stdout.strip()
        
        if "SUCCESS:" in output:
            return True, "Senha alterada com sucesso!"
        elif "ERROR:" in output:
            error_msg = output.split("ERROR:", 1)[1].strip()
            
            # Tratamento de erros conhecidos
            if "0x800708C5" in error_msg or "requisitos de diretiva" in error_msg:
                return False, "A senha não atende aos requisitos de complexidade (mínimo de caracteres, maiúsculas/minúsculas, números) ou já foi utilizada recentemente."
            
            return False, f"Erro AD: {error_msg}"
        else:
            # Caso o script falhe de forma inesperada ou escreva no stderr
            if result.stderr:
                return False, f"Erro Script: {result.stderr.strip()}"
            return False, "Falha desconhecida na execução do reset de senha."

    except Exception as e:
        return False, f"Erro sistema: {str(e)}"



def login_required(f):
    """Decorator para proteger rotas que requerem autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- NOVAS FUNCIONALIDADES DE GESTÃO (PREMIUM) ---

def get_ldap_connection(config, write_mode=False):
    """Helper interno para obter conexão segura ou padrão"""
    # Para escrita (reset senha, modify), preferimos SSL
    # Usando PROTOCOL_TLS_CLIENT para compatibilidade moderna (TLS 1.2+)
    tls = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLS_CLIENT)
    conn = None
    
    # 1. Tenta SSL (636)
    try:
        # connect_timeout aumentado para evitar drops prematuros
        server = Server(config['server'], port=636, use_ssl=True, get_info=ALL, tls=tls, connect_timeout=10)
        user_dn = f"{config['adminUser']}@{config['domain']}"
        conn = Connection(server, user=user_dn, password=config['adminPass'], authentication=SIMPLE)
        if conn.bind(): return conn
    except: pass
    
    # 2. Se não for operação crítica de senha (ou falhar SSL), tenta 389
    if not write_mode:
        try:
            server = Server(config['server'], port=389, get_info=ALL)
            user_dn = f"{config['domain']}\\{config['adminUser']}"
            conn = Connection(server, user=user_dn, password=config['adminPass'], authentication=SIMPLE)
            if conn.bind(): return conn
        except: pass
        
    return None

def unlock_user_account(username):
    """Desbloqueia a conta do usuário (lockoutTime = 0)"""
    config = load_ad_config()
    if not config: return False, "AD não configurado"
    
    try:
        conn = get_ldap_connection(config, write_mode=True)
        if not conn: return False, "Falha ao conectar no AD"
        
        # Busca DN
        conn.search(config['baseDN'], f'(sAMAccountName={username})', attributes=['distinguishedName'])
        if not conn.entries:
            conn.unbind()
            return False, "Usuário não encontrado"
            
        target_dn = str(conn.entries[0].distinguishedName)
        
        # Unlock logic: lockoutTime = 0
        success = conn.modify(target_dn, {'lockoutTime': [(MODIFY_REPLACE, [0])]})
        conn.unbind()
        
        if success: return True, "Conta desbloqueada com sucesso!"
        return False, f"Erro ao desbloquear: {conn.result['description']}"
    except Exception as e:
        return False, str(e)

def toggle_user_status(username, enable=True):
    """Habilita ou Desabilita um usuário (UserAccountControl)"""
    config = load_ad_config()
    if not config: return False, "AD não configurado"
    
    try:
        conn = get_ldap_connection(config, write_mode=True)
        if not conn: return False, "Falha ao conectar no AD"
        
        conn.search(config['baseDN'], f'(sAMAccountName={username})', attributes=['distinguishedName', 'userAccountControl'])
        if not conn.entries:
            conn.unbind()
            return False, "Usuário não encontrado"
            
        target_dn = str(conn.entries[0].distinguishedName)
        current_uac = int(conn.entries[0].userAccountControl.value)
        
        new_uac = current_uac
        if enable:
            # Remove flag ACCOUNTDISABLE (0x0002)
            new_uac = current_uac & ~0x0002
        else:
            # Adiciona flag ACCOUNTDISABLE (0x0002)
            new_uac = current_uac | 0x0002
            
        success = conn.modify(target_dn, {'userAccountControl': [(MODIFY_REPLACE, [new_uac])]})
        conn.unbind()
        
        action = "Habilitado" if enable else "Desabilitado"
        if success: return True, f"Usuário {action} com sucesso!"
        return False, f"Erro ao alterar status: {conn.result['description']}"
    except Exception as e:
        return False, str(e)

def update_ad_attributes(username, updates):
    """
    Atualiza atributos genéricos do usuário
    updates = {'telephoneNumber': '123', 'title': 'Dev'}
    """
    config = load_ad_config()
    if not config: return False, "AD não configurado"
    
    try:
        conn = get_ldap_connection(config, write_mode=True)
        if not conn: return False, "Falha conexão AD"
        
        conn.search(config['baseDN'], f'(sAMAccountName={username})', attributes=['distinguishedName'])
        if not conn.entries:
            conn.unbind()
            return False, "Usuário não encontrado"
            
        target_dn = str(conn.entries[0].distinguishedName)
        
        # Prepara changes map
        changes = {}
        for k, v in updates.items():
            if v:
                changes[k] = [(MODIFY_REPLACE, [v])]
            else:
                # Se vazio, deleta o atributo? Ou seta para espaço?
                # MODIFY_REPLACE com lista vazia geralmente remove em alguns servidores, 
                # mas DELETE é mais seguro. Vamos tentar replace por string vazia ou tratar delete
                changes[k] = [(MODIFY_REPLACE, [])] # Tenta limpar

        success = conn.modify(target_dn, changes)
        conn.unbind()
        
        if success: return True, "Dados atualizados!"
        return False, f"Erro update: {conn.result['description']}"
    except Exception as e:
        return False, str(e)

def get_all_ad_groups():
    """Lista todos os grupos do domínio para o dropdown"""
    config = load_ad_config()
    if not config: return []
    
    try:
        conn = get_ldap_connection(config)
        if not conn: return []
        
        conn.search(config['baseDN'], '(objectClass=group)', attributes=['cn', 'description'])
        groups = []
        for entry in conn.entries:
            groups.append(str(entry.cn))
        
        conn.unbind()
        return sorted(groups)
    except:
        return []

def manage_group_membership(username, group_name, action='add'):
    """
    Adiciona ou remove usuário de um grupo.
    action: 'add' ou 'remove'
    """
    config = load_ad_config()
    if not config: return False, "AD Off"
    
    try:
        conn = get_ldap_connection(config, write_mode=True)
        if not conn: return False, "Erro Conexão"
        
        # 1. Pega DN do usuário
        conn.search(config['baseDN'], f'(sAMAccountName={username})', attributes=['distinguishedName'])
        if not conn.entries: return False, "User not found"
        user_dn = str(conn.entries[0].distinguishedName)
        
        # 2. Pega DN do grupo
        # group_name é apenas o CN (ex: "VPN Users"), precisamos do DN completo
        conn.search(config['baseDN'], f'(&(objectClass=group)(cn={group_name}))', attributes=['distinguishedName'])
        if not conn.entries: return False, "Group not found"
        group_dn = str(conn.entries[0].distinguishedName)
        
        # 3. Executa
        op = None
        from ldap3 import MODIFY_ADD, MODIFY_DELETE
        if action == 'add': op = MODIFY_ADD
        elif action == 'remove': op = MODIFY_DELETE
        else: return False, "Invalid Action"
        
        success = conn.modify(group_dn, {'member': [(op, [user_dn])]})
        conn.unbind()
        
        if success: return True, "Associação de grupo atualizada!"
        return False, f"Erro Grupo: {conn.result['description']}"
        
    except Exception as e:
        return False, str(e)

def get_ad_storage():
    """Lista armazenamento (Failsafe: Verifica status antes do cache)"""
    settings = load_general_settings()
    if not settings.get('ad_enabled', True):
        return []
    return _get_ad_storage_impl()

@cache_result(timeout_minutes=15)
def _get_ad_storage_impl():
    """Implementação real da busca de discos"""
    import subprocess

    script_path = resource_path(os.path.join("scripts", "get_ad_storage.ps1"))
    if not os.path.exists(script_path):
        return []

    try:
        # Só permite busca se houver configuração salva. Se não houver, nada de cache ou busca.
        config = load_ad_config()
        if not config: return []

        # Formato DOMAIN\User é mais seguro para autenticação Windows antiga
        full_user = f"{config.get('domain', '')}\\{config.get('adminUser', '')}"
        password = config.get('adminPass', '')
        
        if full_user and password:
            # Convertemos para SecureString para satisfazer o script
            password_escaped = password.replace("'", "''")
            cmd = [
                "powershell", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", f"& {{ $p = ConvertTo-SecureString '{password_escaped}' -AsPlainText -Force; & '{script_path}' -User '{full_user}' -Password $p }}"
            ]
        else:
            cmd = ["powershell", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path]

        CREATE_NO_WINDOW = 0x08000000
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', creationflags=CREATE_NO_WINDOW)
        
        if result.returncode != 0:
            print(f"Erro PS Shares: {result.stderr}")
            return []
            
        output = result.stdout.strip()
        if not output: return []
        
        # Pode retornar um único objeto ou lista
        data = json.loads(output)
        if isinstance(data, dict): data = [data]
        return data
        
    except Exception as e:
        print(f"Erro buscando shares: {e}")
        return []

def get_failed_logins(hours=24):
    """Lista logins falhados (Failsafe: Verifica status antes do cache)"""
    settings = load_general_settings()
    if not settings.get('ad_enabled', True):
        return []
    return _get_failed_logins_impl(hours)

@cache_result(timeout_minutes=5)
def _get_failed_logins_impl(hours=24):
    """Implementação real da busca de logins falhados"""
    import subprocess

    script_path = resource_path(os.path.join("scripts", "get_failed_logins.ps1"))
    if not os.path.exists(script_path):
        return []

    try:
        # Só permite busca se houver configuração salva
        config = load_ad_config()
        if not config: return []

        full_user = f"{config.get('domain', '')}\\{config.get('adminUser', '')}"
        password = config.get('adminPass', '')
        
        if full_user and password:
            # Passamos o password convertendo para SecureString no próprio comando para satisfazer o script
            password_escaped = password.replace("'", "''")
            cmd = [
                "powershell", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", f"& {{ $p = ConvertTo-SecureString '{password_escaped}' -AsPlainText -Force; & '{script_path}' -User '{full_user}' -Password $p -Hours {hours} }}"
            ]
        else:
            cmd = ["powershell", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path, "-Hours", str(hours)]

        CREATE_NO_WINDOW = 0x08000000
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=60, creationflags=CREATE_NO_WINDOW)
        
        if result.returncode != 0:
            print(f"Erro PS Failed Logins: {result.stderr}")
            return []
            
        output = result.stdout.strip()
        if not output: return []
        
        data = json.loads(output)
        if isinstance(data, dict): data = [data]
        return data
        
    except Exception as e:
        print(f"Erro buscando failed logins: {e}")
        return []

# ===== DASHBOARD HELPER FUNCTIONS =====

def get_all_users():
    """Alias para get_ad_users - compatibilidade com dashboard"""
    return get_ad_users()

def get_disk_alerts(threshold_percent=90):
    """Retorna lista de discos com pouco espaço"""
    try:
        storage = get_ad_storage()
        if not storage:
            return []
        
        alerts = []
        for disk in storage:
            try:
                free_percent = disk.get('FreePercent', 100)
                if free_percent < (100 - threshold_percent):
                    alerts.append(disk)
            except:
                continue
        
        return alerts
    except Exception as e:
        print(f"Erro ao buscar alertas de disco: {e}")
        return []

def get_offline_servers():
    """Retorna lista de servidores offline (stub - implementar depois)"""
    # TODO: Implementar verificação de servidores offline
    # Por enquanto retorna lista vazia
    return []
