import re
import unicodedata
from flask import jsonify, session
from glpi_helper import get_my_tickets, get_ticket_details
from blueprints.ai.intents import find_users_fuzzy

def is_reset_ticket(t):
    def norm(txt):
        return "".join(c for c in unicodedata.normalize('NFD', str(txt).lower()) if unicodedata.category(c) != 'Mn')
    
    name = norm(t.get('name', ''))
    cat = norm(t.get('category_name') or t.get('itilcategory_name') or "")
    content = norm(re.sub('<[^<]+?>', '', str(t.get('content', ''))))
    
    full = f"{name} {cat} {content}"
    keywords = ["reset", "senha", "password", "sneha", "bloqueado", "redefinir", "redefir", "trocar", "acesso"]
    return any(k in full for k in keywords)

def analyze_ticket_for_action(t):
    def norm(txt):
        return "".join(c for c in unicodedata.normalize('NFD', str(txt).lower()) if unicodedata.category(c) != 'Mn')

    name_norm = norm(t.get('name', ''))
    content_norm = norm(re.sub('<[^<]+?>', '', str(t.get('content', ''))))
    
    if not is_reset_ticket(t):
        return None

    search_context = content_norm if len(content_norm) > 5 else name_norm
    triggers = ["senha", "reset", "para", "p/", "de", "do", "da", "usuario", "resetar", "trocar", "redefir", "redefinir", "rede", "acesso"]
    trigger_pattern = rf'\b({"|".join(triggers)})\b'
    
    all_triggers = list(re.finditer(trigger_pattern, search_context))
    if all_triggers:
        last_trigger = all_triggers[-1]
        search_term = search_context[last_trigger.end():].strip()
    else:
        search_term = search_context

    junk_list = ["o", "um", "a", "de", "do", "da", "para", "p/", "resetar", "trocar", "mudar", "senha", "usuario", "solicitacao", "teste", "urgente", "auto", "rede", "redefir", "redefinir", "chamado", "abrir"]
    last_term = None
    while search_term != last_term:
        last_term = search_term
        for word in junk_list:
            search_term = re.sub(rf'^{word}\s+', '', search_term, flags=re.IGNORECASE).strip()
            search_term = re.sub(rf'\s+{word}$', '', search_term, flags=re.IGNORECASE).strip()
        if search_term.lower() in junk_list:
            search_term = ""

    matches = find_users_fuzzy(search_term)
    if not matches and " " in search_term:
        words = [w for w in search_term.split() if len(w) > 2]
        if words:
            short_term = " ".join(words[:2])
            matches = find_users_fuzzy(short_term)
        
    if matches:
        if len(matches) > 3:
            term_parts = set(search_term.lower().split())
            refined = []
            for m in matches:
                d_lower = m['DisplayName'].lower()
                meaningful_parts = [p for p in term_parts if len(p) > 2]
                if all(p in d_lower for p in meaningful_parts):
                    refined.append(m)
            if refined: matches = refined

        return {
            'ticket_id': str(t.get('id')),
            'candidates': matches,
            'user_found_term': search_term
        }
    return None

def get_ai_intelligence_logic():
    from license_manager import lic_manager
    if not lic_manager.has_pro_access(): return jsonify([])
    
    username = session.get('username')
    tickets = get_my_tickets(username)
    if not isinstance(tickets, list): return jsonify([])
    
    seen_alerts = session.get('ai_seen_alerts', [])
    alerts = []
    
    ACTIVE_STATUSES = [1, 2, 3, 4]
    def get_id_val(t):
        try: return int(t.get('id', 0))
        except: return 0
    tickets.sort(key=get_id_val, reverse=True)
    active_pool = [t for t in tickets if int(t.get('status', 0)) in ACTIVE_STATUSES]

    for t in active_pool:
        tid = str(t.get('id'))
        if tid in seen_alerts: continue
        
        t_content = str(t.get('content', '')).lower()
        t_name = str(t.get('name', '')).lower()
        search_blob = f"{t_name} {t_content}"
        keywords = ["senha", "reset", "password", "acesso", "bloqueado", "redefinir", "redefir", "trocar", "esqueci", "expirou", "cair", "travou"]
        
        if not any(k in search_blob for k in keywords): continue

        full_ticket = get_ticket_details(username, tid)
        if full_ticket and not full_ticket.get('error'):
            action = analyze_ticket_for_action(full_ticket)
            if action:
                candidates = action['candidates']
                u = candidates[0]
                desc = f'O chamado #{tid} pede reset para {u["DisplayName"]}'
                if len(candidates) > 1: desc += f' (e outros {len(candidates)-1} possíveis).'
                
                alerts.append({
                    'id': tid, 'type': 'password_reset_request', 'title': 'Chamado de resetar senha',
                    'description': desc, 'ticket_id': tid, 'target_user': u['SamAccountName'], 'target_display': u['DisplayName']
                })
                seen_alerts.append(tid)
            elif is_reset_ticket(full_ticket):
                alerts.append({
                    'id': tid, 'type': 'password_reset_unknown', 'title': 'Reset de Senha Detectado',
                    'description': f'O chamado #{tid} parece ser um reset, mas não identifiquei o usuário no AD.',
                    'ticket_id': tid
                })
                seen_alerts.append(tid)
    
    session['ai_seen_alerts'] = seen_alerts
    return jsonify(alerts)
