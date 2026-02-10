from thefuzz import fuzz
from ad_helper import get_ad_users

# --- INTENT DEFINITIONS ---
INTENTS = {
    'help': ['ajuda', 'help', 'socorro', 'o que voce faz', 'como usar', 'ensine', 'tutorial', 'comandos', 'manual'],
    'reset_password': ['resetar senha', 'mudar senha', 'trocar senha', 'alterar senha', 'reset pwd', 'esqueci senha', 'senha nova', 'sneha', 'senna', 'redefinir senha', 'redefir senha'],
    'network_status': ['como esta a rede', 'status da rede', 'dashboard geral', 'resumo da rede', 'ativos online'],
    'disk_alert': ['disco cheio', 'espaço em disco', 'storage full', 'alerta de disco', 'hd lotado'],
    'cpu_alert': ['cpu alta', 'lento', 'travando', 'processamento', 'quem esta usando cpu'],
    'find_ip': ['buscar ip', 'quem e o ip', 'onde esta o ip', 'rastrear ip'],
    'suggest_ip': ['ip livre', 'ip vago', 'ip disponivel', 'proximo ip', 'sugere ip'],
    'unlock_user': ['desbloquear usuario', 'liberar conta', 'desbloqueia', 'usuario travado', 'conta bloqueada'],
    'user_profile': ['quem sou eu', 'meu perfil', 'meu pc', 'meu computador', 'minha conta'],
    'find_user': ['quem e o usuario', 'perfil do usuario', 'buscar pessoa', 'dados do usuario', 'pessao'],
    'glpi_tickets': ['meus chamados', 'status dos tickets', 'abrir suporte', 'ver chamados', 'verificar chamados', 'tickets ativos', 'meus tickets'],
    'scan_network': ['fazer scan', 'escanear rede', 'varrer agora', 'iniciar varredura'],
    'bulk_disable': ['desabilitar inativos', 'limpar ad', 'bloquear usuarios antigos', 'desativar contas', 'nunca logam', 'nao logam', 'verificar inativos', 'usuarios inativos', 'listar inativos', 'contas antigas'],
    'generate_report': ['gerar relatorio', 'relatorio de disco', 'report pdf', 'listar servidores', 'espaco em disco', 'relatorio de storage'],
    'list_alerts': ['alertas', 'ver alertas', 'alertas do dia', 'listar alertas', 'problemas hoje', 'rotina de alertas', 'erros de hoje', 'alertas criticos'],
    'security_checkup': ['checkup de seguranca', 'auditoria', 'saude da rede', 'como esta a seguranca', 'verificar vulnerabilidades', 'scanner de seguranca', 'analise de risco', 'seguranca']
}

def is_admin_account(username, display_name):
    """Verifica se o usuário é administrativo"""
    u = (username or "").lower()
    d = (display_name or "").lower()
    admin_terms = ["admin", "administrator", "suporte", "root", "system"]
    return any(term in u for term in admin_terms) or any(term in d for term in admin_terms)

def find_users_fuzzy(search_term):
    all_users = get_ad_users()
    search_term = search_term.lower().strip()
    if not search_term: return []

    scored = []
    for u in all_users:
        sam = str(u.get('samaccountname') or u.get('SamAccountName') or u.get('username') or '').strip().lower()
        disp = str(u.get('displayname') or u.get('DisplayName') or '').strip().lower()
        name = str(u.get('name') or u.get('Name') or '').strip().lower()
        
        score = max(
            fuzz.token_set_ratio(search_term, sam),
            fuzz.token_set_ratio(search_term, disp),
            fuzz.token_set_ratio(search_term, name)
        )
        if score > 65: scored.append((u, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    matches = []
    for u, s in scored:
        sam = u.get('samaccountname') or u.get('SamAccountName') or u.get('username')
        display = u.get('displayname') or u.get('DisplayName') or sam
        matches.append({
            'SamAccountName': sam, 
            'DisplayName': display,
            'IsAdmin': is_admin_account(sam, display)
        })
    return matches

def find_assets_fuzzy(term):
    from blueprints.ai.utils import load_scan_data
    assets = load_scan_data()
    term = term.lower().strip()
    matches = []
    for a in assets:
        ip = str(a.get('ip', '')).lower()
        host = str(a.get('hostname', '')).lower()
        user = str(a.get('user', '')).lower()
        if ip == term: return [a]
        if (term in host) or (term in user) or (term in ip):
            matches.append(a)
    return matches
