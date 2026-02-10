# utils.py - Utilitários e validações para estabilidade do sistema
import re
import ipaddress
import os
import json
from functools import wraps
from flask import jsonify
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
item_offset = 0
logger = logging.getLogger('NetAudit')

import sys
import shutil

# --- PERSISTÊNCIA DE DADOS ---
APP_NAME = "NetAudit Enterprise"

def get_data_dir():
    """
    Retorna o diretório de dados persistente (%APPDATA%/NetAudit).
    Cria se não existir.
    """
    appdata = os.getenv('APPDATA')
    if not appdata:
        # Fallback para home do usuário se APPDATA não existir (raro)
        appdata = os.path.expanduser("~")
    
    data_dir = os.path.join(appdata, APP_NAME)
    
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
            logger.info(f"Diretório de dados criado: {data_dir}")
        except Exception as e:
            logger.error(f"Erro ao criar diretório de dados {data_dir}: {e}")
            # Fallback para pasta local se falhar gravação no C:
            return os.getcwd()
            
    return data_dir

def get_data_path(filename):
    """
    Retorna o caminho absoluto para um arquivo na pasta de dados persistente.
    """
    return os.path.join(get_data_dir(), filename)

def migrate_legacy_data():
    """
    Move arquivos da pasta local (onde está o exe) para a pasta persistente (AppData).
    Executado na inicialização.
    """
    local_dir = os.getcwd() # Ou os.path.dirname(sys.executable) se frozen
    if getattr(sys, 'frozen', False):
        local_dir = os.path.dirname(sys.executable)

    data_dir = get_data_dir()
    
    # Se pasta de dados for a mesma da local (dev mode), não faz nada
    if os.path.normpath(local_dir) == os.path.normpath(data_dir):
        return

    files_to_migrate = [
        "netaudit.db",
        "scan_history.json",
        "users.json",
        "general_settings.json",
        "scan_schedule.json",
        "ad_config.json",
        "license.json",
        "glpi_config.json"
    ]

    for filename in files_to_migrate:
        local_path = os.path.join(local_dir, filename)
        # NOVO: Também checa na pasta NetAudit (sem Enterprise) se viemos de versão antiga
        old_data_dir = os.path.join(os.environ.get('APPDATA', ''), "NetAudit")
        old_path = os.path.join(old_data_dir, filename)
        
        target_path = os.path.join(data_dir, filename)
        
        # Só migra se existe no local/antigo e NÃO existe no destino
        if not os.path.exists(target_path):
            source = None
            if os.path.exists(local_path):
                source = local_path
            elif os.path.exists(old_path):
                source = old_path
            
            if source:
                try:
                    shutil.copy2(source, target_path)
                    logger.info(f"Migrado: {filename} -> {target_path}")
                except Exception as e:
                    logger.error(f"Erro ao migrar {filename}: {e}")


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def validate_ip(ip_str):
    """
    Valida se uma string é um IP válido
    
    Args:
        ip_str: String com IP
        
    Returns:
        tuple: (bool, str) - (válido, mensagem de erro)
    """
    try:
        ipaddress.ip_address(ip_str)
        return True, None
    except ValueError as e:
        return False, f"IP inválido: {str(e)}"

def validate_subnet(subnet_str):
    """
    Valida se uma string é uma subnet válida
    
    Args:
        subnet_str: String com subnet (ex: 192.168.1.0/24)
        
    Returns:
        tuple: (bool, str) - (válido, mensagem de erro)
    """
    try:
        # Sanitização básica para erros de digitação comuns
        # Ex: 172.23.51.0;23 -> 172.23.51.0/23
        subnet_str = subnet_str.replace(';', '/').replace(':', '/')
        
        # Corrigir inputs como 172.23.51.1/24 (host bits set) -> aceitar usando strict=False
        # Mas garantir formatação correta.
        
        ipaddress.ip_network(subnet_str, strict=False)
        return True, None
    except ValueError as e:
        return False, f"Subnet inválida: {str(e)}"

def validate_username(username):
    """
    Valida username do AD
    
    Args:
        username: String com username
        
    Returns:
        tuple: (bool, str) - (válido, mensagem de erro)
    """
    if not username or len(username) < 3:
        return False, "Username deve ter pelo menos 3 caracteres"
    
    # Permite letras, números, ponto, hífen e underscore
    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        return False, "Username contém caracteres inválidos"
    
    return True, None

def validate_password(password):
    """
    Valida senha (requisitos mínimos)
    
    Args:
        password: String com senha
        
    Returns:
        tuple: (bool, str) - (válido, mensagem de erro)
    """
    if not password or len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    
    return True, None

def validate_days_threshold(days):
    """
    Valida threshold de dias
    
    Args:
        days: Número de dias
        
    Returns:
        tuple: (bool, str) - (válido, mensagem de erro)
    """
    try:
        days_int = int(days)
        if days_int < 1 or days_int > 365:
            return False, "Dias deve estar entre 1 e 365"
        return True, None
    except (ValueError, TypeError):
        return False, "Dias deve ser um número inteiro"

def api_error_handler(func):
    """
    Decorator para tratamento de erros em APIs
    Captura exceções e retorna JSON com erro
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.error(f"Erro de validação em {func.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }), 400
        except PermissionError as e:
            logger.error(f"Erro de permissão em {func.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'permission_error',
                'message': 'Sem permissão para executar esta operação'
            }), 403
        except FileNotFoundError as e:
            logger.error(f"Arquivo não encontrado em {func.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'file_not_found',
                'message': 'Arquivo ou recurso não encontrado'
            }), 404
        except Exception as e:
            logger.exception(f"Erro inesperado em {func.__name__}")
            return jsonify({
                'success': False,
                'error': 'internal_error',
                'message': 'Erro interno do servidor'
            }), 500
    return wrapper

def safe_json_load(filepath, default=None):
    """
    Carrega JSON de forma segura com fallback
    
    Args:
        filepath: Caminho do arquivo JSON
        default: Valor padrão se falhar
        
    Returns:
        Dados do JSON ou valor padrão
    """
    import json
    import os
    
    if not os.path.exists(filepath):
        logger.warning(f"Arquivo não encontrado: {filepath}, usando valor padrão")
        return default if default is not None else {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON de {filepath}: {str(e)}")
        return default if default is not None else {}
    except Exception as e:
        logger.error(f"Erro ao ler arquivo {filepath}: {str(e)}")
        return default if default is not None else {}

def safe_json_save(filepath, data):
    """
    Salva JSON de forma segura com backup e retry
    
    Args:
        filepath: Caminho do arquivo JSON
        data: Dados para salvar
        
    Returns:
        bool: True se sucesso, False se falhou
    """
    import json
    import os
    import shutil
    import time
    import tempfile
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Criar backup se arquivo existir
            if os.path.exists(filepath):
                backup_path = f"{filepath}.backup"
                try:
                    shutil.copy2(filepath, backup_path)
                    logger.debug(f"Backup criado: {backup_path}")
                except:
                    pass  # Ignora erro de backup
            
            # Escrever em arquivo temporário primeiro (escrita atômica)
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=os.path.dirname(filepath) or '.')
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Força escrita em disco
                
                # Move arquivo temporário para destino (operação atômica no Windows)
                if os.path.exists(filepath):
                    os.replace(temp_path, filepath)
                else:
                    shutil.move(temp_path, filepath)
                
                logger.debug(f"Arquivo salvo com sucesso: {filepath}")
                return True
                
            except Exception as e:
                # Remove arquivo temporário se falhou
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
                raise e
                
        except PermissionError as e:
            logger.warning(f"Tentativa {attempt + 1}/{max_attempts} - Arquivo bloqueado: {filepath}")
            if attempt < max_attempts - 1:
                time.sleep(0.5 * (attempt + 1))  # Backoff exponencial
                continue
            else:
                logger.error(f"Erro ao salvar arquivo {filepath} após {max_attempts} tentativas: {str(e)}")
                
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo {filepath}: {str(e)}")
            break
    
    # Tentar restaurar backup se todas as tentativas falharam
    backup_path = f"{filepath}.backup"
    if os.path.exists(backup_path):
        try:
            shutil.copy2(backup_path, filepath)
            logger.info(f"Backup restaurado: {filepath}")
        except:
            logger.error(f"Falha ao restaurar backup de {filepath}")
    
    return False

def retry_on_failure(max_attempts=3, delay=1):
    """
    Decorator para retry automático em caso de falha
    
    Args:
        max_attempts: Número máximo de tentativas
        delay: Delay entre tentativas (segundos)
    """
    import time
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Tentativa {attempt + 1}/{max_attempts} falhou em {func.__name__}: {str(e)}"
                    )
                    
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            
            logger.error(f"Todas as {max_attempts} tentativas falharam em {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator

def sanitize_filename(filename):
    """
    Remove caracteres perigosos de nomes de arquivo
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        str: Nome sanitizado
    """
    # Remove caracteres perigosos
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove espaços extras
    filename = re.sub(r'\s+', '_', filename)
    
    # Limita tamanho
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def format_bytes(bytes_value):
    """
    Formata bytes para formato legível
    
    Args:
        bytes_value: Valor em bytes
        
    Returns:
        str: Valor formatado (ex: "1.5 GB")
    """
    try:
        bytes_value = float(bytes_value)
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        
        return f"{bytes_value:.2f} PB"
    except (ValueError, TypeError):
        return "N/A"

def format_uptime(seconds):
    """
    Formata uptime em formato legível
    
    Args:
        seconds: Uptime em segundos
        
    Returns:
        str: Uptime formatado (ex: "2d 5h 30m")
    """
    try:
        seconds = int(seconds)
        
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"
    except (ValueError, TypeError):
        return "N/A"

class RateLimiter:
    """
    Rate limiter simples para prevenir abuso de APIs
    """
    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, identifier):
        """
        Verifica se requisição é permitida
        
        Args:
            identifier: Identificador único (ex: IP, username)
            
        Returns:
            bool: True se permitido, False se bloqueado
        """
        import time
        
        now = time.time()
        
        # Limpar requisições antigas
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.window_seconds
            ]
        else:
            self.requests[identifier] = []
        
        # Verificar limite
        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(f"Rate limit excedido para {identifier}")
            return False
        
        # Adicionar nova requisição
        self.requests[identifier].append(now)
        return True

# Instância global do rate limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

# --- GESTÃO DE CONFIGURAÇÕES GERAIS ---
SETTINGS_FILE = get_data_path("general_settings.json")

def load_general_settings():
    """Carrega as configurações gerais do sistema (AD, AI, Tickets)"""
    default = {
        "ai_enabled": True, 
        "ad_enabled": True, 
        "tickets_enabled": True,
        "dashboard_refresh_interval": 30000
    }
    return safe_json_load(SETTINGS_FILE, default=default)

def save_general_settings(config):
    """Salva as configurações gerais do sistema"""
    return safe_json_save(SETTINGS_FILE, config)
