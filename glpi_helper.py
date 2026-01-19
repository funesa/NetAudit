import requests
import urllib3
import json
import os
import threading
import time
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
    if not config: return None
    
    url = config.get('url')
    app_token = config.get('app_token')
    user_token = config.get('user_token')
    login = config.get('auth_user')
    password = config.get('auth_pass')

    with SESSION_LOCK:
        cached = SESSION_CACHE.get(username)
        if cached and time.time() < cached['expires']:
            return cached['token']
    
    # Se não tem no cache ou expirou, inicia nova
    new_token = init_session(url, app_token, user_token, login, password)
    if new_token:
        with SESSION_LOCK:
            SESSION_CACHE[username] = {
                'token': new_token,
                'expires': time.time() + SESSION_TIMEOUT
            }
        return new_token
    return None

def init_session(url, app_token, user_token=None, login=None, password=None):
    """
    Inicia sessão no GLPI e retorna o session_token.
    Prioriza user_token se fornecido, senão usa login/pass.
    """
    # Sanitização da URL: remove index.php e query params, garante base correta
    clean_url = url.split('/index.php')[0].split('?')[0].rstrip('/')
    target_url = f"{clean_url}/apirest.php/initSession"
    
    print(f"[GLPI] Tentando conectar em: {target_url}")
    
    headers = {
        'Content-Type': 'application/json',
        'App-Token': app_token
    }
    
    # Autenticação
    if user_token:
        headers['Authorization'] = f"user_token {user_token}"
    elif login and password:
        # Basic Auth é feito passando Authorization header ou parâmetros,
        # mas requests.auth.HTTPBasicAuth faz o header correto automaticamente
        auth = requests.auth.HTTPBasicAuth(login, password)
        try:
            response = requests.get(target_url, headers=headers, auth=auth, verify=False, timeout=10)
            response.raise_for_status()
            return response.json().get('session_token')
        except Exception as e:
            print(f"[GLPI] Erro initSession (Basic): {e}")
            return None
    
    # Tenta conectar (User Token)
    try:
        print(f"[GLPI] Enviando request para {target_url}")
        response = requests.get(target_url, headers=headers, verify=False, timeout=10)
        
        if response.status_code != 200:
            print(f"[GLPI] Falha: Status Code {response.status_code}")
            print(f"[GLPI] Corpo da resposta: {response.text}")
            
            if response.status_code == 400 and "IP" in response.text:
                return None # IP não autorizado
                
        response.raise_for_status()
        token = response.json().get('session_token')
        print(f"[GLPI] Sucesso! Token: {token[:5]}...")
        return token
    except Exception as e:
        print(f"[GLPI] Erro initSession: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"[GLPI] Response: {e.response.text}")
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
        result = response.json()
        
        # Salva no cache
        TICKETS_CACHE[cache_key] = (result, time.time())
        
        return result
        
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
        
        # Paralelizar sub-recursos com mais workers e timeout menor
        endpoints = {
            'followups': 'ITILFollowup',
            'tasks': 'TicketTask',
            'solutions': 'ITILSolution',
            'actors': 'Ticket_User'
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
