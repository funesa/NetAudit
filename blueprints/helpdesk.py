from flask import Blueprint, render_template, request, jsonify, session
from core.decorators import login_required, tickets_required, premium_required
from glpi_helper import (
    load_glpi_config, save_glpi_config, test_connection, 
    get_my_tickets, get_glpi_stats, get_glpi_categories, 
    get_glpi_locations, add_ticket_followup, add_ticket_solution, 
    create_ticket, get_ticket_details
)

helpdesk_bp = Blueprint('helpdesk', __name__)

@helpdesk_bp.route('/tickets')
@login_required
@tickets_required
@premium_required
def tickets_page():
    return render_template('tickets.html')

@helpdesk_bp.route('/api/glpi/config', methods=['GET', 'POST'])
@login_required
def api_glpi_config():
    username = session.get('username')
    if request.method == 'GET':
        config = load_glpi_config(username) or {}
        return jsonify({
            'configured': bool(config),
            'url': config.get('url', ''),
            'app_token': config.get('app_token', ''),
            'user_token': config.get('user_token', ''),
            'login': config.get('auth_user', ''),
            # Não retornamos a senha por segurança, ou retornamos mascarada? 
            # O front vai precisar saber se é para manter a senha antiga ou usar uma nova.
            # Por simplicidade agora, retornamos tudo, em prod mascarariamos.
            # 'password': config.get('auth_pass', '') 
        })
    
    data = request.json
    success, message = test_connection(data.get('url'), data.get('app_token'), data.get('user_token'), data.get('login'), data.get('password'))
    if success:
        save_glpi_config(username, data)
        return jsonify({'success': True, 'message': 'Conexão OK'})
    return jsonify({'success': False, 'message': message})

@helpdesk_bp.route('/api/glpi/tickets')
@login_required
def api_glpi_tickets():
    username = session.get('username')
    status_filter = request.args.get('status', 'not_solved')
    tickets = get_my_tickets(username)
    
    if isinstance(tickets, dict) and 'error' in tickets:
        return jsonify({'success': False, 'error': tickets['error']})
    
    filtered = []
    if isinstance(tickets, list):
        for t in tickets:
            sid = t.get('status', 0)
            if status_filter == 'not_solved' and sid in [1, 2, 3, 4]: filtered.append(t)
            elif status_filter == 'solved' and sid in [5, 6]: filtered.append(t)
            elif status_filter == 'all': filtered.append(t)
                
    return jsonify({'success': True, 'tickets': filtered})

@helpdesk_bp.route('/api/glpi/stats')
@login_required
def api_glpi_stats():
    return jsonify(get_glpi_stats(session.get('username')))

@helpdesk_bp.route('/api/glpi/categories')
@login_required
def api_glpi_categories():
    return jsonify(get_glpi_categories(session.get('username')))

@helpdesk_bp.route('/api/glpi/locations')
@login_required
def api_glpi_locations():
    return jsonify(get_glpi_locations(session.get('username')))

@helpdesk_bp.route('/api/glpi/ticket/<int:ticket_id>', methods=['GET'])
@login_required
def api_glpi_ticket_detail(ticket_id):
    return jsonify(get_ticket_details(session.get('username'), ticket_id))

@helpdesk_bp.route('/api/glpi/ticket/<int:ticket_id>/followup', methods=['POST'])
@login_required
def api_glpi_add_followup(ticket_id):
    content = request.json.get('content')
    if not content: return jsonify({'success': False, 'message': 'Conteúdo vazio'})
    return jsonify(add_ticket_followup(session.get('username'), ticket_id, content))

@helpdesk_bp.route('/api/glpi/ticket/create', methods=['POST'])
@login_required
def api_glpi_create_ticket():
    data = request.json
    title = data.get('title')
    content = data.get('content')
    if not title or not content:
        return jsonify({'success': False, 'message': 'Título e conteúdo são obrigatórios'})
    
    extra = {
        'category': data.get('category'),
        'location': data.get('location'),
        'urgency': data.get('urgency', 3)
    }
    return jsonify(create_ticket(session.get('username'), title, content, extra))

@helpdesk_bp.route('/api/glpi/upload', methods=['POST'])
@login_required
def api_glpi_upload_document():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
    
    file = request.files['file']
    itemtype = request.form.get('itemtype', 'Ticket')
    items_id = request.form.get('items_id')
    
    if not items_id:
        return jsonify({'success': False, 'message': 'ID do item obrigatório'})
        
    result = upload_glpi_document(
        session.get('username'),
        file.read(),
        file.filename,
        itemtype,
        items_id
    )
    return jsonify(result)

@helpdesk_bp.route('/api/glpi/document/<int:doc_id>')
@login_required
def api_glpi_download_document(doc_id):
    from flask import Response
    import requests
    
    username = session.get('username')
    config = load_glpi_config(username)
    session_token = get_session(username)
    
    if not config or not session_token:
        return "Não autorizado", 401
        
    url = get_glpi_document_link(username, doc_id)
    headers = {
        'App-Token': config['app_token'],
        'Session-Token': session_token
    }
    
    req = requests.get(url, headers=headers, stream=True, verify=False)
    
    return Response(
        req.iter_content(chunk_size=1024),
        content_type=req.headers.get('Content-Type'),
        headers={
            'Content-Disposition': req.headers.get('Content-Disposition', f'attachment; filename=document_{doc_id}')
        }
    )
