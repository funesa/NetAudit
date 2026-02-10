import requests
import urllib3
import json
import os
import base64
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from utils import safe_json_load, safe_json_save
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração de Session com pool de conexões e retry
def create_optimized_session():
    """Cria uma sessão HTTP otimizada com pool de conexões e retry"""
    session = requests.Session()
    
    # Retry strategy para falhas temporárias
    retry_strategy = Retry(
        total=2,  # Máximo 2 tentativas
        backoff_factor=0.3,  # Espera 0.3s entre tentativas
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    
    # Adapter com pool de conexões
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,  # Pool de 10 conexões
        pool_maxsize=20,  # Máximo 20 conexões simultâneas
        pool_block=False
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Headers otimizados
    session.headers.update({
        'Accept-Encoding': 'gzip, deflate',  # Compressão
        'Connection': 'keep-alive'  # Reutiliza conexão
    })
    
    return session

# Session global otimizada
OPTIMIZED_SESSION = create_optimized_session()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração Padrão
CONFIG_FILE = 'glpi_config.json'

# Debug Logger
def debug_glpi(msg):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("glpi_debug.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except: pass

# Arquivo para salvar configs por usuário
# Estrutura: { "username": { "url": "...", "app_token": "...", "user_token": "...", "auth_user": "...", "auth_pass": "..." } }
GLPI_CONFIG_FILE = "glpi_config.json"

def load_glpi_config(username):
    """Carrega configuração do GLPI para um usuário específico"""
    data = safe_json_load(GLPI_CONFIG_FILE, default={})
    return data.get(username)

def save_glpi_config(username, config):
    """Salva configuração do GLPI para um usuário"""
    data = safe_json_load(GLPI_CONFIG_FILE, default={})
    data[username] = config
    return safe_json_save(GLPI_CONFIG_FILE, data)

# Cache de sessões em memória
# Estrutura: { "username": { "token": "...", "expires": timestamp } }
SESSION_CACHE = {}
SESSION_TIMEOUT = 1800 # 30 minutos
SESSION_LOCK = threading.Lock()

def get_session(username):
    """Retorna um session_token válido do cache ou cria um novo"""
    config = load_glpi_config(username)
    if not config: 
        debug_glpi(f"get_session: Config não encontrada para {username}")
        return None
    
    url = config.get('url', '').strip()
    app_token = config.get('app_token', '').strip()
    user_token = config.get('user_token', '').strip()
    login = config.get('auth_user') or config.get('login') # Fallback para compatibilidade
    if login: login = login.strip()
    password = config.get('auth_pass') or config.get('password')
    if password: password = password.strip()

    with SESSION_LOCK:
        cached = SESSION_CACHE.get(username)
        if cached and time.time() < cached['expires']:
            return cached['token']
    
    # Se não tem no cache ou expirou, inicia nova
    debug_glpi(f"get_session: Iniciando nova sessão para {username} em {url}")
    new_token = init_session(url, app_token, user_token, login, password)
    if new_token:
        with SESSION_LOCK:
            SESSION_CACHE[username] = {
                'token': new_token,
                'expires': time.time() + SESSION_TIMEOUT
            }
        return new_token
    
    debug_glpi(f"get_session: Falha ao obter token para {username}")
    return None

def init_session(url, app_token, user_token=None, login=None, password=None):
    """
    Inicia sessão no GLPI e retorna o session_token.
    Prioriza user_token se fornecido, senão usa login/pass.
    """
    if not url: return None
    
    # Sanitização da URL: remove index.php e query params, garante base correta
    clean_url = url.split('/index.php')[0].split('?')[0].rstrip('/')
    target_url = f"{clean_url}/apirest.php/initSession"
    
    debug_glpi(f"init_session: Tentando conectar em {target_url} (Auth: {'UserToken' if user_token else 'Basic'})")
    
    headers = {
        'Content-Type': 'application/json',
        'App-Token': app_token
    }
    
    try:
        # Autenticação
        response = None
        if user_token:
            headers['Authorization'] = f"user_token {user_token}"
            response = requests.get(target_url, headers=headers, verify=False, timeout=10)
        elif login and password:
            # Tenta via Header primeiro
            credentials = f"{login}:{password}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f"Basic {b64_credentials}"
            response = requests.get(target_url, headers=headers, verify=False, timeout=10)
            
            # Se falhou por parâmetros faltando, tenta via Query String (fallback comum em GLPI)
            if response.status_code == 400 and "LOGIN_PARAMETERS_MISSING" in response.text:
                debug_glpi("init_session: Header falhou, tentando via query parameters...")
                params = {'login': login, 'password': password}
                response = requests.get(target_url, headers={'App-Token': app_token}, params=params, verify=False, timeout=10)
        else:
            debug_glpi("init_session: Falta credencial (UserToken ou Login/Senha)")
            return None

        if response.status_code == 200:
            token = response.json().get('session_token')
            debug_glpi("init_session: Sucesso!")
            return token
        else:
            debug_glpi(f"init_session: Falha HTTP {response.status_code} - {response.text}")
            return None

    except Exception as e:
        debug_glpi(f"init_session: Exception - {str(e)}")
        return None

# Cache de tickets em memória (além do cache de sessão)
TICKETS_CACHE = {}
TICKETS_CACHE_TTL = 30  # 30 segundos (Tempo Real)

def get_my_tickets(username):
    """Pega os tickets do usuário logado usando cache de sessão E cache de dados"""
    
    # Verifica cache de tickets primeiro
    cache_key = f"tickets_{username}"
    if cache_key in TICKETS_CACHE:
        cached_data, timestamp = TICKETS_CACHE[cache_key]
        if time.time() - timestamp < TICKETS_CACHE_TTL:
            return cached_data
    
    config = load_glpi_config(username)
    if not config:
        return {'error': 'Not configured'}
    
    url = config.get('url')
    app_token = config.get('app_token')
    
    # 1. Obter Sessão (Cache ou New)
    session_token = get_session(username)
    if not session_token:
        return {'error': 'Auth failed'}
    
    # 2. Buscar Tickets
    target_url = f"{url.rstrip('/')}/apirest.php/Ticket"
    headers = {
        'Content-Type': 'application/json',
        'App-Token': app_token,
        'Session-Token': session_token
    }
    
    try:
        params = {
            'range': '0-30',  # Reduzido de 50 para 30 (carrega menos, mais rápido)
            'expand_dropdowns': 'true',
            'get_hateoas': 'false',
            'sort': 'id',
            'order': 'DESC',
            'with_devices': 'false',
            'with_disks': 'false',
            'with_softwares': 'false',
            'with_connections': 'false',
            'with_networkports': 'false',
            'with_infocoms': 'false',  # Não carrega info financeira
            'with_contracts': 'false',  # Não carrega contratos
            'with_documents': 'false',  # Não carrega documentos
            'with_tickets': 'false',  # Não carrega tickets relacionados
            'with_problems': 'false',  # Não carrega problemas
            'with_changes': 'false'  # Não carrega mudanças
        } 
        response = OPTIMIZED_SESSION.get(target_url, headers=headers, params=params, verify=False, timeout=(3, 5))  # connect=3s, read=5s
        
        # Se 401, a sessão no cache pode ter caído no servidor. Invalida e tenta mais uma vez.
        if response.status_code == 401:
            with SESSION_LOCK:
                if username in SESSION_CACHE: del SESSION_CACHE[username]
            session_token = get_session(username)
            if session_token:
                headers['Session-Token'] = session_token
                response = OPTIMIZED_SESSION.get(target_url, headers=headers, params=params, verify=False, timeout=(3, 5))
        
        response.raise_for_status()
        raw_result = response.json()
        
        # Normalização dos dados para o frontend (extração de nomes expandidos)
        tickets = []
        if isinstance(raw_result, list):
            for t in raw_result:
                # Extração Robusta de Metadados (Tenta vários campos comuns do GLPI)
                
                # 1. Localização
                loc = t.get('_locations_id') or t.get('locations_id')
                if isinstance(loc, dict):
                    t['location'] = loc.get('completename') or loc.get('name')
                
                # 2. Requerente (Tenta Recipient e Requester)
                req = t.get('_users_id_recipient') or t.get('users_id_recipient') or \
                      t.get('_users_id_requester') or t.get('users_id_requester')
                if isinstance(req, dict):
                    t['requester_name'] = req.get('completename') or req.get('name') or req.get('realname')
                
                # 3. Categoria
                cat = t.get('_itilcategories_id') or t.get('itilcategories_id')
                if isinstance(cat, dict):
                    t['category_name'] = cat.get('completename') or cat.get('name')
                
                tickets.append(t)
        
        # Salva no cache
        TICKETS_CACHE[cache_key] = (tickets, time.time())
        
        return tickets
        
    except Exception as e:
        print(f"[GLPI] Erro getTickets: {e}")
        return {'error': str(e)}

def get_ticket_details(username, ticket_id):
    """Retorna detalhes completos usando paralelismo para sub-recursos e cache de sessão"""
    config = load_glpi_config(username)
    if not config: return {'error': 'Not configured'}
    
    url = config.get('url')
    app_token = config.get('app_token')
    
    session_token = get_session(username)
    if not session_token: return {'error': 'Auth failed'}
    
    headers = {
        'Content-Type': 'application/json',
        'App-Token': app_token,
        'Session-Token': session_token
    }
    
    try:
        base_url = url.rstrip('/')
        ticket_url = f"{base_url}/apirest.php/Ticket/{ticket_id}?expand_dropdowns=true"
        r_ticket = requests.get(ticket_url, headers=headers, verify=False, timeout=5)
        
        if r_ticket.status_code == 401:
            with SESSION_LOCK:
                if username in SESSION_CACHE: del SESSION_CACHE[username]
            session_token = get_session(username)
            if session_token:
                headers['Session-Token'] = session_token
                r_ticket = requests.get(ticket_url, headers=headers, verify=False, timeout=5)
        
        r_ticket.raise_for_status()
        ticket_data = r_ticket.json()
        
        # Extração Robusta de Metadados (Tenta vários campos comuns do GLPI)
        
        # 1. Localização
        loc = ticket_data.get('_locations_id') or ticket_data.get('locations_id')
        if isinstance(loc, dict):
            ticket_data['location'] = loc.get('completename') or loc.get('name')
        
        # 2. Requerente (Tenta Recipient e Requester)
        req = ticket_data.get('_users_id_recipient') or ticket_data.get('users_id_recipient') or \
              ticket_data.get('_users_id_requester') or ticket_data.get('users_id_requester')
        if isinstance(req, dict):
            ticket_data['requester_name'] = req.get('completename') or req.get('name') or req.get('realname')
        
        # 3. Categoria
        cat = ticket_data.get('_itilcategories_id') or ticket_data.get('itilcategories_id')
        if isinstance(cat, dict):
            ticket_data['category_name'] = cat.get('completename') or cat.get('name')
        
        # Paralelizar sub-recursos com mais workers e timeout menor
        endpoints = {
            'followups': 'ITILFollowup',
            'tasks': 'TicketTask',
            'solutions': 'ITILSolution',
            'actors': 'Ticket_User',
            'documents': 'Document_Item'
        }
        
        def fetch_sub(key, endpoint):
            try:
                u = f"{base_url}/apirest.php/Ticket/{ticket_id}/{endpoint}?expand_dropdowns=true"
                r = requests.get(u, headers=headers, verify=False, timeout=2)  # Reduzido de 3s para 2s
                if r.status_code == 200:
                    data = r.json()
                    return key, list(data.values()) if isinstance(data, dict) else data
                return key, []
            except: return key, []

        # Aumentar workers para 12 para paralelismo máximo (era 8)
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = [executor.submit(fetch_sub, k, e) for k, e in endpoints.items()]
            for future in futures:
                key, result = future.result()
                ticket_data[key] = result
        
        return ticket_data
    except Exception as e:
        print(f"[GLPI] Erro getTicketDetails: {e}")
        return {'error': str(e)}

def get_glpi_stats(username):
    """Retorna contagem de chamados por status para dashboard"""
    tickets = get_my_tickets(username)
    if isinstance(tickets, dict) and 'error' in tickets: return tickets
    
    stats = {
        'total': 0,
        'new': 0,        # 1
        'processing': 0, # 2
        'planned': 0,    # 3
        'pending': 0,    # 4
        'solved': 0,     # 5
        'closed': 0      # 6
    }
    
    if isinstance(tickets, list):
        stats['total'] = len(tickets)
        for t in tickets:
            s = t.get('status')
            if s == 1: stats['new'] += 1
            elif s == 2: stats['processing'] += 1
            elif s == 3: stats['planned'] += 1
            elif s == 4: stats['pending'] += 1
            elif s == 5: stats['solved'] += 1
            elif s == 6: stats['closed'] += 1
            
    return stats

def get_glpi_categories(username):
    """Busca categorias ITIL disponíveis"""
    config = load_glpi_config(username)
    session_token = get_session(username)
    if not session_token: return []
    
    url = f"{config.get('url').rstrip('/')}/apirest.php/ITILCategory?range=0-100"
    headers = {'App-Token': config.get('app_token'), 'Session-Token': session_token}
    
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return list(data.values()) if isinstance(data, dict) else data
        return []
    except: return []

def get_glpi_locations(username):
    """Busca localidades cadastradas"""
    config = load_glpi_config(username)
    session_token = get_session(username)
    if not session_token: return []
    
    url = f"{config.get('url').rstrip('/')}/apirest.php/Location?range=0-100"
    headers = {'App-Token': config.get('app_token'), 'Session-Token': session_token}
    
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return list(data.values()) if isinstance(data, dict) else data
        return []
    except: return []

def add_ticket_followup(username, ticket_id, content):
    """Adiciona um acompanhamento a um chamado existente"""
    config = load_glpi_config(username)
    if not config: return {'error': 'Not configured'}
    
    session_token = get_session(username)
    if not session_token: return {'error': 'Auth failed'}
    
    headers = {
        'Content-Type': 'application/json',
        'App-Token': config.get('app_token'),
        'Session-Token': session_token
    }
    
    url = f"{config.get('url').rstrip('/')}/apirest.php/Ticket/{ticket_id}/ITILFollowup"
    payload = {"input": {"itemtype": "Ticket", "items_id": ticket_id, "content": content}}
    
    try:
        r = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
        if r.status_code == 401:
            with SESSION_LOCK:
                if username in SESSION_CACHE: del SESSION_CACHE[username]
            session_token = get_session(username)
            if session_token:
                headers['Session-Token'] = session_token
                r = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
        
        r.raise_for_status()
        return {'success': True, 'data': r.json()}
    except Exception as e:
        print(f"[GLPI] Erro addFollowup: {e}")
        return {'success': False, 'error': str(e)}

def add_ticket_solution(username, ticket_id, content):
    """Adiciona uma solução a um chamado existente"""
    config = load_glpi_config(username)
    if not config: return {'error': 'Not configured'}
    
    session_token = get_session(username)
    if not session_token: return {'error': 'Auth failed'}
    
    headers = {
        'Content-Type': 'application/json',
        'App-Token': config.get('app_token'),
        'Session-Token': session_token
    }
    
    url = f"{config.get('url').rstrip('/')}/apirest.php/Ticket/{ticket_id}/ITILSolution"
    # solution_type=1 (Default)
    payload = {"input": {"itemtype": "Ticket", "items_id": ticket_id, "content": content, "solutiontypes_id": 1}}
    
    try:
        r = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
        if r.status_code == 401:
            with SESSION_LOCK:
                if username in SESSION_CACHE: del SESSION_CACHE[username]
            session_token = get_session(username)
            if session_token:
                headers['Session-Token'] = session_token
                r = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
        
        r.raise_for_status()
        return {'success': True, 'data': r.json()}
    except Exception as e:
        print(f"[GLPI] Erro addSolution: {e}")
        return {'success': False, 'error': str(e)}

def create_ticket(username, title, content, extra_params=None):
    """Cria um novo chamado no GLPI com parâmetros avançados"""
    config = load_glpi_config(username)
    if not config: return {'error': 'Not configured'}
    
    session_token = get_session(username)
    if not session_token: return {'error': 'Auth failed'}
    
    headers = {
        'Content-Type': 'application/json',
        'App-Token': config.get('app_token'),
        'Session-Token': session_token
    }
    
    url = f"{config.get('url').rstrip('/')}/apirest.php/Ticket"
    
    ticket_input = {
        "name": title,
        "content": content,
        "urgency": 3, # Média default
        "impact": 3   # Média default
    }
    
    if extra_params:
        if 'category' in extra_params: ticket_input["itilcategories_id"] = extra_params['category']
        if 'urgency' in extra_params: ticket_input["urgency"] = extra_params['urgency']
        if 'impact' in extra_params: ticket_input["impact"] = extra_params['impact']
        if 'location' in extra_params: ticket_input["locations_id"] = extra_params['location']
    
    payload = {"input": ticket_input}
    
    try:
        r = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
        if r.status_code == 401:
            with SESSION_LOCK:
                if username in SESSION_CACHE: del SESSION_CACHE[username]
            session_token = get_session(username)
            if session_token:
                headers['Session-Token'] = session_token
                r = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
        
        r.raise_for_status()
        return {'success': True, 'data': r.json()}
    except Exception as e:
        print(f"[GLPI] Erro createTicket: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response error: {e.response.text}")
        return {'success': False, 'error': str(e)}

def test_connection(url, app_token, user_token, login, password):
    """Testa credenciais (bypass cache para teste real)"""
    token = init_session(url, app_token, user_token, login, password)
    if token:
        # Aproveita e já coloca no cache se funcionou
        return True, "Conexão bem sucedida!"
    return False, "Falha na autenticação. Verifique credenciais."
def upload_glpi_document(username, file_bytes, filename, itemtype="Ticket", items_id=None):
    """Envia um arquivo para o GLPI e vincula a um item (chamado ou acompanhamento)"""
    config = load_glpi_config(username)
    if not config: return {'success': False, 'message': 'GLPI não configurado'}
    
    session_token = get_session(username)
    if not session_token: return {'success': False, 'message': 'Falha na sessão'}
    
    url = config['url'].rstrip('/')
    headers = {
        'App-Token': config['app_token'],
        'Session-Token': session_token
    }
    
    target_url = f"{url}/apirest.php/Document"
    
    # Manifest de upload exigido pelo GLPI
    manifest = {
        "input": {
            "name": filename,
            "_itemtype": itemtype,
            "_items_id": items_id
        }
    }
    
    try:
        files = {
            'uploadManifest': (None, json.dumps(manifest), 'application/json'),
            'filename[0]': (filename, file_bytes)
        }
        
        response = requests.post(target_url, headers=headers, files=files, verify=False, timeout=30)
        
        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json()}
        else:
            return {'success': False, 'message': f"Falha no upload GLPI: {response.text}"}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_glpi_document_link(username, document_id):
    """Retorna o link de download para um documento (usado pelo proxy)"""
    config = load_glpi_config(username)
    if not config: return None
    
    session_token = get_session(username)
    if not session_token: return None
    
    url = config['url'].rstrip('/')
    # O GLPI permite download via /Document/{id}?alt=media ou similar dependendo da versão
    return f"{url}/apirest.php/Document/{document_id}?alt=media"

def update_ticket(username, ticket_id, data):
    """Atualiza metadados de um chamado (ex: status, categoria, etc)"""
    config = load_glpi_config(username)
    if not config: return {'error': 'Not configured'}
    
    session_token = get_session(username)
    if not session_token: return {'error': 'Auth failed'}
    
    headers = {
        'Content-Type': 'application/json',
        'App-Token': config.get('app_token'),
        'Session-Token': session_token
    }
    
    url = f"{config.get('url').rstrip('/')}/apirest.php/Ticket/{ticket_id}"
    payload = {"input": data}
    
    try:
        r = requests.put(url, headers=headers, json=payload, verify=False, timeout=10)
        if r.status_code == 401:
            with SESSION_LOCK:
                if username in SESSION_CACHE: del SESSION_CACHE[username]
            session_token = get_session(username)
            if session_token:
                headers['Session-Token'] = session_token
                r = requests.put(url, headers=headers, json=payload, verify=False, timeout=10)
        
        r.raise_for_status()
        return {'success': True, 'data': r.json()}
    except Exception as e:
        print(f"[GLPI] Erro updateTicket: {e}")
        return {'success': False, 'error': str(e)}
