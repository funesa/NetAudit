from flask import Blueprint, request, jsonify
import re
import json
import os
import difflib
from ad_helper import reset_ad_password, unlock_user_account, toggle_user_status, get_ad_users

def get_settings():
    try:
        from utils import load_general_settings
        return load_general_settings()
    except:
        return {"ad_enabled": True, "tickets_enabled": True, "ai_enabled": True}

ai_bp = Blueprint('ai_actions', __name__)

def load_scan_data():
    """Carrega o histórico de ativos escaneados (scan_history.json)"""
    try:
        from utils import get_data_path
        db_path = get_data_path("scan_history.json")
        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else list(data.values())
    except Exception as e:
        print(f"Erro ao carregar scan DB: {e}")
    return []

def find_assets_fuzzy(term):
    """Busca ativos por Hostname, IP ou Usuário logado"""
    assets = load_scan_data()
    term = term.lower()
    matches = []
    
    for a in assets:
        # Extrai campos principais
        ip = str(a.get('ip', '')).lower()
        host = str(a.get('hostname', '')).lower()
        user = str(a.get('user', '')).lower()
        
        # 1. Match exato de IP (Prioridade)
        if ip == term:
            return [a]
        
        # 2. Match parcial em Hostname ou User
        if (term in host) or (term in user) or (term in ip):
            matches.append(a)
            
    return matches

def find_users_fuzzy(search_term):
    """
    Busca usuários no AD (cache) que correspondam ao termo de busca.
    Retorna lista de dicionários com {username, name, email}.
    """
    all_users = get_ad_users() # Retorna dicts
    search_term = search_term.lower()
    
    matches = []
    
    # Debug: Print keys to confirm structure if needed
    # if all_users: print(f"DEBUG JS KEYS: {all_users[0].keys()}")

    for u in all_users:
        # Normalização de chaves para evitar case sensitivity
        u_lower = {k.lower(): v for k, v in u.items()}
        
        # Extração usando as chaves corretas definidas em get_ad_users.ps1
        # O script PS retorna: username, displayName, email, description, etc.
        sam = str(u_lower.get('username', '')).strip()
        display = str(u_lower.get('displayname', '')).strip()
        email = str(u_lower.get('email', '')).strip() # Script usa 'email', não 'emailaddress'
        
        # Limpeza de "N/A" que o script PS pode retornar
        if sam == "N/A": sam = ""
        if display == "N/A": display = ""
        if email == "N/A": email = ""

        # Definição do Nome de Exibição 
        final_name = display if display else sam
        
        # Objeto normalizado para retorno consistente no backend
        clean_user = {
            'SamAccountName': sam,
            'DisplayName': final_name,
            'EmailAddress': email,
            'Description': str(u_lower.get('description', ''))
        }
        
        sam_lower = sam.lower()
        final_name_lower = final_name.lower()
        search_lower = search_term.lower()
        
        # Validação essencial
        if not sam: continue

        # 1. Match Exato de Username (Prioridade Máxima)
        if sam_lower == search_lower:
             return [clean_user] 
            
        # 2. Match Parcial (Username ou Nome Completo)
        if (search_lower in sam_lower) or (search_lower in final_name_lower):
            matches.append(clean_user)
            
    return matches

def format_user_display(u):
    return f"{u.get('DisplayName', 'N/A')} ({u.get('SamAccountName')})"

def format_asset_card(asset):
    """Gera HTML rico para exibir detalhes de um ativo"""
    icon = asset.get('icon', 'ph-desktop')
    vendor = asset.get('vendor', 'Genérico')
    status_color = "#10b981" if asset.get('status_code', 'ONLINE') == 'ONLINE' else "#ef4444"
    
    return f"""
    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
        <div style="width: 50px; height: 50px; background: rgba(59, 130, 246, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #60a5fa; font-size: 1.5rem;">
            <i class="ph-fill {icon}"></i>
        </div>
        <div style="flex: 1;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0; color: white; font-size: 1rem;">{asset.get('hostname', 'Unknown')}</h4>
                <span style="font-size: 0.75rem; background: {status_color}20; color: {status_color}; padding: 2px 8px; border-radius: 99px;">{asset.get('ip')}</span>
            </div>
            <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px;">
                {asset.get('os_detail', 'OS Desconhecido')} • {asset.get('user', 'Sem usuário')}
            </div>
             <div style="color: #64748b; font-size: 0.75rem; margin-top: 2px;">
                {vendor} • {asset.get('model', 'N/A')}
            </div>
        </div>
    </div>
    """

def ping_ip(ip):
    """Verifica se um IP responde a ping (1 pacote, timeout curto)"""
    import subprocess, platform
    try:
        param_n = '-n' if platform.system().lower() == 'windows' else '-c'
        param_w = '-w' if platform.system().lower() == 'windows' else '-W'
        # Timeout 500ms (so não demorar muito na UI)
        command = ['ping', param_n, '1', param_w, '500', ip]
        creationflags = 0x08000000 if platform.system().lower() == 'windows' else 0
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags) == 0
    except:
        return False


def suggest_free_ips(count=1):
    """ Encontra um ou mais IPs livres na sub-rede principal (baseado no histórico) """
    assets = load_scan_data()
    if not assets: return []
    
    # 1. Infere a sub-rede mais comum (ex: 172.23.51)
    from collections import Counter
    subnets = []
    used_host_parts = set() # Apenas o ultimo octeto
    
    base_subnet = ""
    
    for a in assets:
        ip = a.get('ip')
        if ip and '.' in ip:
            parts = ip.split('.')
            if len(parts) == 4:
                subnet = ".".join(parts[:3])
                subnets.append(subnet)
                if subnet == base_subnet or not base_subnet:
                     used_host_parts.add(int(parts[3]))
    
    if subnets:
        base_subnet = Counter(subnets).most_common(1)[0][0]
        # Recalcula used hosts apenas para a subnet vencedora
        used_host_parts = set()
        for a in assets:
             ip = a.get('ip')
             if ip and ip.startswith(base_subnet):
                 parts = ip.split('.')
                 used_host_parts.add(int(parts[3]))
    else:
        return [] # Sem dados para inferir
        
    # 2. Procura slots livres
    import random
    candidates = list(range(20, 254)) 
    random.shuffle(candidates) # Embaralha para variar a sugestão
    
    found_ips = []
    for host_num in candidates:
        if len(found_ips) >= count:
            break
            
        if host_num in used_host_parts:
            continue # Já existe no banco de dados como ativo
            
        candidate_ip = f"{base_subnet}.{host_num}"
        
        # 3. Valida com Ping (Realtime Check)
        if not ping_ip(candidate_ip):
            found_ips.append(candidate_ip)
            
    return found_ips

def suggest_free_ip():
    """ Versão simplificada para manter compatibilidade reversa """
    ips = suggest_free_ips(1)
    return ips[0] if ips else None

from license_manager import lic_manager

@ai_bp.route('/api/ai/process', methods=['POST'])
def process_command():
    # 1. Licença Check
    if not lic_manager.has_pro_access():
         return jsonify({
            'intent': 'error',
            'description': 'A Atena IA é um recurso Premium. O seu trial expirou ou você não possui uma licença ativa.',
            'params': {}
        }), 403

    # Check if AI is enabled in general settings
    try:
        from utils import safe_json_load
        settings = safe_json_load("general_settings.json", default={"ai_enabled": True})
        if not settings.get("ai_enabled", True):
            return jsonify({
                'intent': 'error',
                'description': 'A Atena IA está desativada no momento. Reative-a nas Configurações do Sistema.',
                'params': {}
            }), 403
    except:
        pass

    data = request.json
    command = data.get('command', '').lower()

    # --- IP AVAILABILITY CHECK (Specific IP) ---
    # "o ip 10.0.0.1 está livre?", "ip 10.0.0.1 disponivel"
    check_match = re.search(r'(?:o\s+)?ip\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(?:est[áa]|t[áa]|é)?\s*(?:livre|dispon[íi]vel|vago|usado|ocupado)', command)
    
    if check_match:
        target_ip = check_match.group(1)
        
        # 1. Verifica no Histórico
        known_assets = find_assets_fuzzy(target_ip)
        is_known = len(known_assets) > 0
        known_asset_online = is_known and known_assets[0].get('status_code') == 'ONLINE'
        
        # 2. Verificação em Tempo Real (Ping)
        is_responding = ping_ip(target_ip)
        
        if is_responding:
            # Caso 1: Responde Ping = OCUPADO
            status_text = "OCUPADO"
            color = "#ef4444" 
            icon = "ph-prohibit"
            
            detail_html = ""
            if is_known:
                asset = known_assets[0]
                detail_html = f"""
                <div style="margin-top:10px; padding:10px; background:rgba(255,255,255,0.05); border-radius:8px;">
                     <strong>Identificado como:</strong> {asset.get('hostname')} ({asset.get('vendor')})
                     <br><small>Usuário: {asset.get('user')}</small>
                </div>
                """
            else:
                 detail_html = "<div style='margin-top:10px; font-size:0.9em; color:#9ca3af;'>Dispositivo desconhecido, mas responde ao Ping.</div>"

            html = f"""
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                <div style="background:{color}20; color:{color}; padding:8px; border-radius:50%;"><i class="ph-fill {icon} size-lg"></i></div>
                <div>
                    <h4 style="margin:0; color:{color};">IP {target_ip} em uso</h4>
                </div>
            </div>
            {detail_html}
            """
            
            return jsonify({
                'intent': 'show_info',
                'description': html,
                'params': {}
            })
            
        elif is_known and known_asset_online:
             # Caso 2: Não pinga agora, mas consta ONLINE no banco recente
             html = f"""
             <h4 style="color:#f59e0b; margin:0 0 10px 0;">🚫 IP Possivelmente em Uso</h4>
             <p>O IP <strong>{target_ip}</strong> não respondeu ao ping agora, mas consta como <strong>ONLINE</strong> no último scan do sistema.</p>
             {format_asset_card(known_assets[0])}
             """
             return jsonify({'intent': 'show_info', 'description': html, 'params': {}})
             
        else:
            # Caso 3: LIVRE
            html = f"""
            <div style="text-align:center; padding:15px;">
                <div style="display:inline-flex; background:rgba(16, 185, 129, 0.2); color:#34d399; padding:15px; border-radius:50%; margin-bottom:10px;">
                    <i class="ph-fill ph-check-circle" style="font-size:2rem;"></i>
                </div>
                <h3 style="color:#34d399; margin:5px 0;">IP Disponível</h3>
                <p style="color:#cbd5e1; margin-top:5px;">O IP <strong>{target_ip}</strong> parece estar livre.</p>
                <div style="text-align:left; font-size:0.85rem; color:#94a3b8; margin-top:15px; padding:10px; background:rgba(0,0,0,0.2); border-radius:8px;">
                    <div style="margin-bottom:4px"><i class="ph-bold ph-check" style="color:#34d399; margin-right:6px;"></i> Sem resposta de Ping</div>
                    <div><i class="ph-bold ph-check" style="color:#34d399; margin-right:6px;"></i> Não consta no scanner</div>
                </div>
            </div>
            """
            return jsonify({'intent': 'show_info', 'description': html, 'params': {}})

    # --- SUGGEST FREE IP ---
    # "me arruma um ip livre", "qual ip está livre", "sugerir ip", "preciso de um ip", "5 ips livres"
    # Agora detecta se tiver "ip" e "livre/vago/disponivel" na mesma frase, e olha por números
    has_ip_term = "ip" in command or "ips" in command
    has_free_term = any(t in command for t in ["livre", "vago", "dispon", "disponível", "disponivel"])
    
    if has_ip_term and has_free_term:
        # Tenta extrair um número da frase
        count_match = re.search(r'(\d+)', command)
        count = int(count_match.group(1)) if count_match else 1
        
        # Limite de segurança para não demorar demais no processamento
        if count > 10: count = 10
        
        free_ips = suggest_free_ips(count)
        
        if free_ips:
            if len(free_ips) == 1:
                html = f"""
                <div style="text-align:center; padding:15px;">
                    <div style="margin-bottom:10px; font-size:0.9rem; color:#94a3b8;">Sugestão de IP livre:</div>
                    <div style="background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16, 185, 129, 0.3); color:#34d399; padding:15px; border-radius:12px;">
                        <h2 style="margin:0; font-family:monospace; letter-spacing:1px;">{free_ips[0]}</h2>
                    </div>
                </div>
                """
            else:
                ips_html = "".join([f'<div style="background:rgba(16, 185, 129, 0.1); border:1px solid rgba(16, 185, 129, 0.2); color:#34d399; padding:6px 10px; border-radius:6px; font-family:monospace; font-weight:bold; font-size:1rem; text-align:center; min-width: 120px;">{ip}</div>' for ip in free_ips])
                html = f"""
                <div style="width: 100%; box-sizing: border-box;">
                    <div style="margin-bottom:12px; font-size:0.9rem; color:#94a3b8;">Encontrei <strong>{len(free_ips)}</strong> IPs que parecem estar livres:</div>
                    <div style="display:flex; flex-wrap:wrap; gap:8px; justify-content: center;">
                        {ips_html}
                    </div>
                    <div style="margin-top:15px; font-size:0.75rem; color:#64748b; font-style:italic; text-align:center;">
                        Estes IPs não responderam ao ping e não constam no banco de dados.
                    </div>
                </div>
                """
            return jsonify({'intent': 'show_info', 'description': html, 'params': {}})
        else:
             return jsonify({'intent': 'show_info', 'description': "Não consegui identificar uma sub-rede segura ou IPs livres no momento.", 'params': {}})
             
    # --- ASSET INTELLIGENCE (Endereços IP, Hostnames, PCs) ---
    
    # 1. IP Query: "quem é o ip X", "X" (genérico)
    # Regex flexível para capturar IPs IPv4
    ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', command)
    if ip_match:
        target_ip = ip_match.group(0)
        assets = find_assets_fuzzy(target_ip)
        
        if assets:
            html = "<h3 class='ai-confirm-text'>Dispositivo Encontrado</h3>" + "".join([format_asset_card(a) for a in assets])
            return jsonify({
                'intent': 'show_info',
                'description': html,
                'confirmation_text': 'Detalhes do Ativo',
                'params': {}
            })
            
    # 2. Hostname/Asset Query: "detalhes do pc X", "onde esta o computador X", "mostre a maquina X"
    asset_match = re.search(r'(?:detalhes|ver|mostrar|buscar|quem .|onde .|info)\s+(?:d[oa]s?)?\s*(?:pc|computador|m[áa]quina|host|ativo|servidor)\s+(.+)', command)
    if asset_match:
        target_raw = asset_match.group(1).strip()
        assets = find_assets_fuzzy(target_raw)
        
        if assets:
            html = f"<h3 class='ai-confirm-text'>Resultados para '{target_raw}'</h3>" + "".join([format_asset_card(a) for a in assets[:5]])
            return jsonify({
                'intent': 'show_info',
                'description': html,
                'confirmation_text': f'Encontrei {len(assets)} dispositivo(s)',
                'params': {}
            })
        else:
             return jsonify({'intent': 'uknown', 'message': f'Nenhum dispositivo encontrado com o nome "{target_raw}".'})

    # --- USER ACTIONS (AD REQUIRED) ---
    settings = get_settings()
    ad_enabled = settings.get('ad_enabled', True)
    
    # Check if command is AD-related
    is_ad_cmd = any(word in command for word in ['senha', 'usuario', 'usuário', 'desbloque', 'desabilit', 'habilit', 'ad ', 'active'])
    
    if is_ad_cmd and not ad_enabled:
        return jsonify({
            'intent': 'show_info',
            'description': '🔴 As funcionalidades de Active Directory estão desativadas nas configurações do sistema.',
            'confirmation_text': 'AD Desativado',
            'params': {}
        })
    
    # 3. Reset Password
    # Structure A (Complete): [action] [user] para [password]
    password_pattern = r'(?:reset(?:ar|a)?|mud(?:ar|a)|alter(?:ar|a)|troc(?:ar|a)|defin(?:ir|e)|reet(?:ar|a)?)\s+(?:a\s+|sua\s+)?(?:senha\s+)?(?:d[eoa]s?|o|a)?\s*(.+?)\s+para\s+(\S+)'
    password_match = re.search(password_pattern, command)
    
    # Structure B (Partial - Missing Password): [action] [user]
    # Usado apenas se o completo falhar
    password_pattern_partial = r'(?:reset(?:ar|a)?|mud(?:ar|a)|alter(?:ar|a)|troc(?:ar|a)|defin(?:ir|e)|reet(?:ar|a)?)\s+(?:a\s+|sua\s+)?(?:senha\s+)?(?:d[eoa]s?|o|a)?\s*(.+)'
    
    target_raw = None
    new_password = None
    
    if password_match:
        target_raw = password_match.group(1).strip()
        new_password = password_match.group(2).strip()
    elif re.search(password_pattern_partial, command):
        match_partial = re.search(password_pattern_partial, command)
        target_raw = match_partial.group(1).strip()
        # new_password continua None
    
    if target_raw:
        # Se capturou "senha de pablo", target_raw é "pablo".
        # Evita capturar comandos de outros tipos
        if "desbloque" in command or "desabilit" in command:
             target_raw = None # Deixa passar para os outros handlers
        
    if target_raw:
        candidates = find_users_fuzzy(target_raw)
        
        if len(candidates) == 0:
             all_count = len(get_ad_users())
             return jsonify({
                'intent': 'uknown', 
                'message': f'Não encontrei nenhum usuário correspondente a "{target_raw}". (Base pesquisada: {all_count} usuários)'
            })
            
        if len(candidates) > 1:
            # Ambiguidade
            candidate_list = []
            for c in candidates:
                candidate_list.append({
                    'username': c.get('SamAccountName'),
                    'name': c.get('DisplayName'),
                    'info': c.get('Description') or c.get('EmailAddress') or ''
                })
                
            return jsonify({
                'intent': 'ambiguous',
                'description': f'Encontrei {len(candidates)} usuários para "{target_raw}". Selecione um:',
                'candidates': candidate_list,
                'pending_action': 'reset_password',
                'pending_params': {'password': new_password} # Pode ser None
            })
            
        # Match Único
        target_user = candidates[0]
        username = target_user.get('SamAccountName')
        
        if not new_password:
            # Fluxo conversacional: Pede a senha
            return jsonify({
                'intent': 'incomplete_password',
                'description': f'Entendido. Encontrei o usuário <strong>{username}</strong> ({target_user.get("DisplayName")}).\nQual será a nova senha?',
                'pending_action': 'reset_password',
                'pending_params': {'username': username}
            })
        
        # Fluxo Completo
        return jsonify({
            'intent': 'reset_password',
            'description': f'Este comando irá alterar a senha do usuário AD <strong>{username}</strong> ({target_user.get("DisplayName")}).',
            'dangerous': True,
            'params': {
                'username': username,
                'password': new_password
            },
            'confirmation_text': f'Deseja alterar a senha de {username} para "{new_password}"?'
        })

    # 4. Unlock User
    # Synonyms: desbloqueia/desbloquear, libera/liberar, destrava/destravar
    unlock_pattern = r'(?:desbloque(?:ar|a)|liber(?:ar|a)|destrav(?:ar|a)|solt(?:ar|a))\s+(?:o\s+|a\s+)?(?:usu[aá]rio|conta)?\s*(?:d[eoa]s?)?\s*(.+)'
    unlock_match = re.search(unlock_pattern, command)
    
    if unlock_match:
        target_raw = unlock_match.group(1).strip()
        candidates = find_users_fuzzy(target_raw)

        if len(candidates) == 0:
             all_count = len(get_ad_users())
             return jsonify({
                'intent': 'uknown', 
                'message': f'Não encontrei nenhum usuário correspondente a "{target_raw}". (Base: {all_count})'
            })

        if len(candidates) > 1:
            candidate_list = [{'username': c.get('SamAccountName'), 'name': c.get('DisplayName')} for c in candidates]
            return jsonify({
                'intent': 'ambiguous',
                'description': f'Encontrei múltiplos usuários. Quem você quer desbloquear?',
                'candidates': candidate_list,
                'pending_action': 'unlock_user',
                'pending_params': {}
            })

        target_user = candidates[0]
        username = target_user.get('SamAccountName')
        
        return jsonify({
            'intent': 'unlock_user',
            'description': f'Este comando irá desbloquear a conta do usuário <strong>{username}</strong> ({target_user.get("DisplayName")}).',
            'dangerous': False,
            'params': {
                'username': username
            },
            'confirmation_text': f'Deseja desbloquear o usuário {username}?'
        })
        
    # 5. Disable User
    # Synonyms: desabilita/desabilitar, desativa/desativar, bloqueia/bloquear
    disable_pattern = r'(?:desabilit(?:ar|a)|desativ(?:ar|a)|bloque(?:ar|a)|inativ(?:ar|a))\s+(?:o\s+|a\s+)?(?:usu[aá]rio|conta)?\s*(?:d[eoa]s?)?\s*(.+)'
    disable_match = re.search(disable_pattern, command)
    
    if disable_match:
        target_raw = disable_match.group(1).strip()
        candidates = find_users_fuzzy(target_raw)
        
        if len(candidates) == 0: 
            return jsonify({'intent': 'uknown', 'message': f'Usuário "{target_raw}" não encontrado.'})
            
        if len(candidates) > 1:
            candidate_list = [{'username': c.get('SamAccountName'), 'name': c.get('DisplayName')} for c in candidates]
            return jsonify({
                'intent': 'ambiguous',
                'description': f'Múltiplos usuários encontrados.',
                'candidates': candidate_list,
                'pending_action': 'disable_user',
                'pending_params': {'action': 'disable'}
            })
            
        target_user = candidates[0]
        username = target_user.get('SamAccountName')

        return jsonify({
            'intent': 'disable_user',
            'description': f'Este comando irá DESATIVAR a conta de <strong>{username}</strong> ({target_user.get("DisplayName")}).',
            'dangerous': True,
            'params': {
                'username': username,
                'action': 'disable'
            },
            'confirmation_text': f'Tem certeza que deseja bloquear o usuário {username}?'
        })

    return jsonify({'intent': 'uknown', 'message': 'Posso ajudar com senhas, desbloqueios e agora também com **ativos de rede**! Tente "detalhes do pc [nome]" ou "quem é o ip [ip]".'})

@ai_bp.route('/api/ai/execute', methods=['POST'])
def execute_command():
    if not lic_manager.has_pro_access():
        return jsonify({'success': False, 'message': 'Recurso Premium necessário.'}), 403

    data = request.json
    intent = data.get('intent')
    params = data.get('params')

    if intent == 'reset_password':
        success, msg = reset_ad_password(params['username'], params['password'])
        return jsonify({'success': success, 'message': msg})
    
    if intent == 'unlock_user':
        success, msg = unlock_user_account(params['username'])
        return jsonify({'success': success, 'message': msg})

    if intent == 'disable_user':
        success, msg = toggle_user_status(params['username'])
        return jsonify({'success': success, 'message': msg})

    return jsonify({'success': False, 'message': 'Ação desconhecida'})
