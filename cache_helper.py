#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sistema de cache persistente para consultas AD"""

from datetime import datetime, timedelta
from functools import wraps
import json
import os

# Arquivo de cache persistente
CACHE_FILE = "ad_cache.json"

# Cache em memória
_cache = {}

def load_cache_from_disk():
    """Carrega o cache do disco ao iniciar"""
    global _cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Converte strings de data de volta para objetos datetime
                for key, val in data.items():
                    _cache[key] = (val[0], datetime.fromisoformat(val[1]))
            print(f"✓ Cache carregado do disco: {len(_cache)} itens")
        except Exception as e:
            print(f"! Erro ao carregar cache do disco: {e}")
            _cache = {}

def save_cache_to_disk():
    """Salva o cache no disco"""
    try:
        data_to_save = {}
        for key, val in _cache.items():
            # Converte datetime para string ISO para JSON
            data_to_save[key] = (val[0], val[1].isoformat())
        
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"! Erro ao salvar cache no disco: {e}")

# Carrega o cache imediatamente ao importar o módulo
load_cache_from_disk()

def cache_result(timeout_minutes=60):
    """Decorator para cachear resultados de funções com persistência"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Cria chave única baseada na função e argumentos
            cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            
            # Verifica se tem cache válido
            if cache_key in _cache:
                cached_data, cached_time = _cache[cache_key]
                if datetime.now() - cached_time < timedelta(minutes=timeout_minutes):
                    print(f"✓ Cache HIT: {func.__name__}")
                    return cached_data
            
            # Executa função e cacheia resultado
            print(f"✗ Cache MISS: {func.__name__} - Consultando AD...")
            result = func(*args, **kwargs)
            
            # Só cacheia se o resultado não for pazio ou erro (dependendo da função)
            if result:
                _cache[cache_key] = (result, datetime.now())
                save_cache_to_disk()
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Limpa todo o cache (memória e disco)"""
    global _cache
    _cache.clear() # Limpeza profunda da referência
    if os.path.exists(CACHE_FILE):
        try: 
            os.remove(CACHE_FILE)
            print(f"✓ Arquivo de cache {CACHE_FILE} removido.")
        except Exception as e:
            print(f"! Erro ao remover {CACHE_FILE}: {e}")
    print("✓ Cache em memória limpo!")
