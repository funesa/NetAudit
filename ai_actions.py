from flask import Blueprint, request, jsonify, session
import re
import json
import os
import unicodedata
from ad_helper import reset_ad_password, toggle_user_status, get_ad_users
from glpi_helper import add_ticket_solution, update_ticket
from license_manager import lic_manager
from core.decorators import login_required
from blueprints.ai.intents import INTENTS, find_users_fuzzy, find_assets_fuzzy, is_admin_account
from blueprints.ai.utils import format_user_card, format_asset_card, ping_ip, load_scan_data
from blueprints.ai.reports import generate_report_logic
from blueprints.ai.tickets import analyze_ticket_for_action, get_ai_intelligence_logic, is_reset_ticket

def get_settings():
    try:
        from utils import load_general_settings
        return load_general_settings()
    except:
        return {"ad_enabled": True, "tickets_enabled": True, "ai_enabled": True}

ai_bp = Blueprint('ai_actions', __name__)

@ai_bp.route('/api/ai/cancel', methods=['POST'])
@login_required
def cancel_context():
    session.pop('ai_context', None)
    return jsonify({'success': True})

@ai_bp.route('/api/ai/process', methods=['POST'])
@login_required
def process_command():
    if not lic_manager.has_pro_access(): return jsonify({'description': 'Premium necessário.'}), 403
    settings = get_settings()
    if not settings.get("ai_enabled", True): return jsonify({'description': 'Atena IA desativada.'}), 403

    command_raw = request.json.get('command', '').strip()
    if not command_raw: return jsonify({'message': 'Diga algo!'})

    command_norm = "".join(c for c in unicodedata.normalize('NFD', command_raw.lower())
                   if unicodedata.category(c) != 'Mn')

    ai_context = session.get('ai_context')

    # 0. Cancelar / Limpar
    if command_norm in ['cancelar', 'sair', 'esquece', 'pare', 'abortar']:
        session.pop('ai_context', None)
        session.pop('ambiguous_ticket_id', None)
        return jsonify({'description': 'Operação cancelada. Como posso ajudar agora?'})

    # 1. Ticket Shortcut
    ticket_match = re.search(r'chamado\s*#?\s*(\d+)', command_norm)
    if ticket_match:
        session.pop('ai_context', None)
        session.pop('ambiguous_ticket_id', None)
        tid = ticket_match.group(1)
        from glpi_helper import get_ticket_details
        t = get_ticket_details(session.get('username'), tid)
        if t and not t.get('error'):
            action = analyze_ticket_for_action(t)
            if action:
                candidates = action['candidates']
                if len(candidates) == 1:
                    u = candidates[0]
                    return jsonify({
                        'intent': 'authorize_ticket_reset',
                        'description': f'Identifiquei que o chamado <strong>#{tid}</strong> é um pedido de reset para <strong>{u["DisplayName"]} ({u["SamAccountName"]})</strong>.<br><br>Deseja autorizar a Atena?',
                        'params': {'username': u['SamAccountName'], 'display': u['DisplayName'], 'ticket_id': tid}
                    })
                else:
                    session['ambiguous_ticket_id'] = tid
                    options_html = f"<div style='margin-bottom:10px;'>O chamado <strong>#{tid}</strong> menciona '<em>{action.get('user_found_term', 'alguém')}</em>', mas encontrei {len(candidates)} opções. Qual delas?:</div>"
                    candidates.sort(key=lambda x: len(x['SamAccountName']))
                    for c in candidates[:5]:
                        options_html += f"<button onclick=\"window.atenaMessage('Eu quero o {c['SamAccountName']}')\" style='display:block; width:100%; text-align:left; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); padding:10px; border-radius:10px; margin-bottom:6px; color:white; cursor:pointer;'><strong>{c['DisplayName']}</strong><br><small style='opacity:0.6'>{c['SamAccountName']}</small></button>"
                    return jsonify({'description': options_html})
        return jsonify({'description': f'Analisei o chamado #{tid}, mas não encontrei um pedido claro de reset de senha.'})

    # 2. Ambiguity Handling
    if command_norm.startswith('eu quero o'):
        target_sam = re.sub(r'(?i)^eu quero o\s+', '', command_raw).strip()
        all_users = get_ad_users()
        selected_user = next((u for u in all_users if (str(u.get('samaccountname') or u.get('SamAccountName') or '')).lower() == target_sam.lower()), None)
        if not selected_user:
            cand = find_users_fuzzy(target_sam)
            if cand: selected_user = {'SamAccountName': cand[0]['SamAccountName'], 'DisplayName': cand[0]['DisplayName']}
        
        if selected_user:
            u_sam = selected_user.get('samaccountname') or selected_user.get('SamAccountName')
            u_disp = selected_user.get('displayname') or selected_user.get('DisplayName') or u_sam
            if is_admin_account(u_sam, u_disp):
                session.pop('ai_context', None)
                return jsonify({'description': '🔴 Não tenho permissão para alterar contas administrativas.'})
            ticket_context = session.get('ambiguous_ticket_id')
            if ticket_context:
                session.pop('ambiguous_ticket_id', None)
                return jsonify({
                    'intent': 'authorize_ticket_reset',
                    'description': f'Certo! Reset de <strong>{u_disp} ({u_sam})</strong> no chamado <strong>#{ticket_context}</strong> confirmado.<br><br>Deseja autorizar a Atena?',
                    'params': {'username': u_sam, 'display': u_disp, 'ticket_id': ticket_context}
                })
            session['ai_context'] = {'state': 'AWAITING_PWD_VAL', 'username': u_sam, 'display': u_disp}
            return jsonify({'description': f'Usuário **{u_disp} ({u_sam})** selecionado. Agora, digite a **nova senha** para ele:'})

    # 3. Contextual States
    if ai_context:
        if ai_context.get('state') == 'AWAITING_PWD_VAL':
            pw = command_raw
            u, d = ai_context.get('username'), ai_context.get('display')
            session['ai_context'] = {'state': 'AWAITING_PWD_FINAL', 'username': u, 'password': pw, 'display': d, 'ticket_id': ai_context.get('ticket_id')}
            return jsonify({
                'intent': 'reset_password',
                'description': f'Resumo da ação:<br>• Usuário: <strong>{d}</strong><br>• Nova Senha: <code>{pw}</code><br><br>Deseja confirmar o reset agora?',
                'params': {'username': u, 'password': pw, 'ticket_id': ai_context.get('ticket_id')},
                'dangerous': True
            })
        if ai_context.get('state') == 'AWAITING_PWD_USER':
            cand = find_users_fuzzy(command_raw)
            if not cand: return jsonify({'description': f'Usuário "{command_raw}" não encontrado. Tente novamente:'})
            if len(cand) == 1:
                u, d = cand[0]['SamAccountName'], cand[0]['DisplayName']
                if is_admin_account(u, d):
                    session.pop('ai_context', None)
                    return jsonify({'description': '🔴 Contas admin não podem ser manipuladas via IA.'})
                session['ai_context'] = {'state': 'AWAITING_PWD_VAL', 'username': u, 'display': d}
                return jsonify({'description': f'Entendido! Qual será a **nova senha** para <strong>{d} ({u})</strong>?'})
            else:
                options_html = "<div style='margin-bottom:10px;'>Vários encontrados. Quem é o alvo?</div>"
                for c in cand[:5]:
                    options_html += f"<button onclick=\"window.atenaMessage('Eu quero o {c['SamAccountName']}')\" style='display:block; width:100%; text-align:left; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); padding:10px; border-radius:10px; margin-bottom:6px; color:white;'><strong>{c['DisplayName']}</strong><br><small style='opacity:0.6'>{c['SamAccountName']}</small></button>"
                return jsonify({'description': options_html})

    # 4. Intent Detection
    from thefuzz import fuzz
    best_intent, best_score = None, 0
    for intent, phrases in INTENTS.items():
        for phrase in phrases:
            score = fuzz.token_set_ratio(command_norm, phrase)
            if score > best_score: best_score, best_intent = score, intent
    if best_score < 60: best_intent = None

    if best_intent == 'help':
        from flask import render_template
        return jsonify({'intent': 'show_info', 'description': render_template('ai_manual.html')})

    if best_intent == 'reset_password':
        parts = re.split(r' para | p/ ', command_norm)
        pw = parts[1].strip() if len(parts) > 1 else None
        target = re.sub(r'.*(?:senha|sneha|resetar|trocar|mudar|de|do|da)\s+', '', parts[0]).strip()
        if target and len(target) > 2:
            cand = find_users_fuzzy(target)
            if cand:
                if len(cand) == 1:
                    u, d = cand[0]['SamAccountName'], cand[0]['DisplayName']
                    if is_admin_account(u, d): return jsonify({'description': '🔴 Não altero admins.'})
                    if pw: return jsonify({'intent': 'reset_password', 'description': f'Confirmar reset de <strong>{d}</strong> para <code>{pw}</code>?', 'dangerous': True, 'params': {'username': u, 'password': pw}})
                    session['ai_context'] = {'state': 'AWAITING_PWD_VAL', 'username': u, 'display': d}
                    return jsonify({'description': f'Certo, localizei <strong>{d}</strong>. Qual a nova senha? (Padrão: <code>Funesa2026</code>)'})
                else:
                    session['ai_context'] = {'state': 'AWAITING_PWD_USER'}
                    options_html = "<div style='margin-bottom:10px;'>Achei vários. Clique no correto:</div>"
                    for c in cand[:5]:
                        options_html += f"<button onclick=\"window.atenaMessage('Eu quero o {c['SamAccountName']}')\" style='display:block; width:100%; text-align:left; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); padding:10px; border-radius:10px; margin-bottom:6px; color:white;'><strong>{c['DisplayName']}</strong><br><small style='opacity:0.6'>{c['SamAccountName']}</small></button>"
                    return jsonify({'description': options_html})
        session['ai_context'] = {'state': 'AWAITING_PWD_USER'}
        return jsonify({'description': 'Com certeza. Qual o **nome ou usuário** da pessoa?'})

    if best_intent == 'glpi_tickets':
        session.pop('ai_seen_alerts', None)
        from glpi_helper import get_my_tickets
        tickets = get_my_tickets(session.get('username'))
        if isinstance(tickets, list) and tickets:
            html = "<div style='margin-bottom:12px;'>Localizei seus chamados abertos:</div>"
            active_statuses = [1, 2, 3, 4]
            recent = [t for t in tickets if int(t.get('status', 0)) in active_statuses][:5]
            for t in recent:
                tid = t.get('id')
                html += f"""<div onclick="window.atenaMessage('Sobre o chamado #{tid}')" style="cursor:pointer; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:10px; border-radius:12px; margin-bottom:8px;">
                    <span style="color:#a78bfa; font-weight:bold;">#{tid}</span> {t.get('name')}</div>"""
            return jsonify({'description': html})
        return jsonify({'description': 'Não encontrei chamados abertos.'})

    if best_intent == 'generate_report':
        return generate_report_logic(command_norm)

    # Fallback to general intents
    return jsonify({'description': 'Não entendi bem... Tente pedir por um nome de usuário, "resetar senha" ou "ajuda".'})

@ai_bp.route('/api/ai/intelligence', methods=['GET'])
@login_required
def get_ai_intelligence():
    return get_ai_intelligence_logic()

@ai_bp.route('/api/ai/execute', methods=['POST'])
@login_required
def execute_command():
    if not lic_manager.has_pro_access(): return jsonify({'success': False, 'message': 'Premium necessário.'}), 403
    data = request.json
    intent, params = data.get('intent'), data.get('params')
    
    if intent == 'reset_password':
        session.pop('ai_context', None)
        u, pw = params['username'], params['password']
        tid = params.get('ticket_id')
        s, m = reset_ad_password(u, pw)
        if s and tid:
            glpi_msg = f"<p>[ATENA IA] Senha de <strong>{u}</strong> redefinida para <code>{pw}</code>.</p>"
            add_ticket_solution(session.get('username'), tid, glpi_msg)
            update_ticket(session.get('username'), tid, {"status": 6})
            m = f"✅ Sucesso! Senha de <strong>{u}</strong> definida. Chamado <strong>#{tid}</strong> encerrado."
        return jsonify({'success': s, 'message': m})

    if intent == 'authorize_ticket_reset':
        u, d, tid = params['username'], params['display'], params['ticket_id']
        pw = "Funesa2026"
        session['ai_context'] = {'state': 'AWAITING_PWD_FINAL', 'username': u, 'password': pw, 'display': d, 'ticket_id': tid}
        return jsonify({
            'success': True, 'intent': 'reset_password',
            'description': f'👤 Usuário: <strong>{d}</strong><br>🔑 Senha: <code>{pw}</code><br>🎫 Chamado: <strong>#{tid}</strong><br><br>Confirmar?',
            'params': {'username': u, 'password': pw, 'ticket_id': tid},
            'dangerous': True
        })
    
    if intent == 'bulk_confirm':
        ctx = session.get('ai_context')
        if not ctx or ctx.get('state') != 'AWAITING_BULK_CONFIRM': return jsonify({'success': False, 'message': 'Sessão expirou.'})
        targets = ctx.get('targets', [])
        success_count = 0
        for sam in targets:
            ok, _ = toggle_user_status(sam, enable=False)
            if ok: success_count += 1
        session.pop('ai_context', None)
        return jsonify({'success': True, 'message': f"✅ {success_count} usuários desabilitados."})

    return jsonify({'success': False, 'message': 'Ação desconhecida.'})

def suggest_free_ips(count=1):
    assets = load_scan_data()
    if not assets: return []
    from collections import Counter
    subnets = [".".join(a.get('ip','').split('.')[:3]) for a in assets if '.' in a.get('ip','')]
    if not subnets: return []
    base = Counter(subnets).most_common(1)[0][0]
    used = set([int(a.get('ip','').split('.')[-1]) for a in assets if a.get('ip','').startswith(base)])
    found, cand = [], list(range(20, 254))
    import random
    random.shuffle(cand)
    for host in cand:
        if len(found) >= count: break
        ip = f"{base}.{host}"
        if host not in used and not ping_ip(ip): found.append(ip)
    return found
