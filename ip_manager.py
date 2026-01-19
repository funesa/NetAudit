# ip_manager.py - Gerenciamento inteligente de IPs
import json
import os
from datetime import datetime, timedelta
import ipaddress

def load_scan_history():
    """Carrega histórico de scans"""
    history_file = 'scan_history.json'
    if not os.path.exists(history_file):
        return []
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def get_active_subnet():
    """Tenta recuperar a subnet ativa do agendamento ou histórico"""
    # 1. Tenta Configuração de Schedule (Prioridade)
    try:
        schedule_file = 'scan_schedule.json'
        if os.path.exists(schedule_file):
            with open(schedule_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('subnet'): 
                    return data.get('subnet')
    except:
        pass

    # 2. Infere do Histórico (Mais comum /24)
    try:
        history = load_scan_history()
        if history:
            from collections import Counter
            subnets = []
            for item in history:
                ip = item.get('ip')
                if ip and '.' in ip:
                    # Assume /24 por padrão para inferência
                    parts = ip.split('.')
                    if len(parts) == 4:
                        subnets.append(f"{parts[0]}.{parts[1]}.{parts[2]}.0/24")
            
            if subnets:
                return Counter(subnets).most_common(1)[0][0]
    except:
        pass
        
    return None

def get_ip_map(subnet=None, days_threshold=7):
    """
    Retorna mapa inteligente de IPs
    """
    if not subnet:
        subnet = get_active_subnet()
        
    if not subnet:
        return {'ips': [], 'stats': {'total': 0, 'error': 'Nenhuma subnet definida'}}

    history = load_scan_history()
    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError:
         return {'ips': [], 'stats': {'total': 0, 'error': f'Subnet inválida: {subnet}'}}
    
    # Dicionário para armazenar info de cada IP
    ip_map = {}
    
    # Inicializar todos os IPs da subnet
    for ip in network.hosts():
        ip_str = str(ip)
        ip_map[ip_str] = {
            'ip': ip_str,
            'status': 'free',  # free, probably_free, in_use, online
            'hostname': None,
            'last_seen': None,
            'last_seen_days': None,
            'mac': None,
            'device_type': None,
            'manufacturer': None
        }
    
    # Analisar histórico
    now = datetime.now()
    
    for entry in history:
        ip = entry.get('ip')
        if ip not in ip_map:
            continue
        
        # Parsear timestamp - usar 'last_updated_at' que é o campo correto
        timestamp_str = entry.get('last_updated_at') or entry.get('timestamp')
        if timestamp_str:
            try:
                # Remove timezone info se houver
                timestamp_str_clean = timestamp_str.replace('Z', '').replace('+00:00', '')
                last_seen = datetime.fromisoformat(timestamp_str_clean)
                
                # Calcular diferença em horas e dias
                time_diff = now - last_seen
                hours_ago = time_diff.total_seconds() / 3600
                days_ago = time_diff.days
                
                # Atualizar se for mais recente
                current_last_seen = ip_map[ip]['last_seen']
                if current_last_seen is None or last_seen > datetime.fromisoformat(current_last_seen.replace('Z', '').replace('+00:00', '')):
                    ip_map[ip]['last_seen'] = timestamp_str
                    ip_map[ip]['last_seen_days'] = days_ago
                    ip_map[ip]['hostname'] = entry.get('hostname')
                    ip_map[ip]['mac'] = entry.get('mac')
                    ip_map[ip]['device_type'] = entry.get('device_type')
                    ip_map[ip]['manufacturer'] = entry.get('vendor')  # vendor é o campo correto
                    
                    # Determinar status baseado em quando foi visto pela última vez
                    # Online: visto nos últimos 30 minutos (scan recente)
                    # Em uso: visto nos últimos X dias (mas não nos últimos 30 min)
                    # Provavelmente livre: visto há mais de X dias
                    if hours_ago <= 0.5:  # 30 minutos
                        ip_map[ip]['status'] = 'online'
                    elif days_ago <= days_threshold:
                        ip_map[ip]['status'] = 'in_use'
                    else:
                        ip_map[ip]['status'] = 'probably_free'
            except Exception as e:
                print(f"Erro ao processar IP {ip}: {e}")
                pass
    
    # Converter para lista e ordenar por IP
    result = sorted(ip_map.values(), key=lambda x: ipaddress.ip_address(x['ip']))
    
    # Estatísticas
    stats = {
        'total': len(result),
        'free': sum(1 for x in result if x['status'] == 'free'),
        'probably_free': sum(1 for x in result if x['status'] == 'probably_free'),
        'in_use': sum(1 for x in result if x['status'] == 'in_use'),
        'online': sum(1 for x in result if x['status'] == 'online'),
        'subnet': subnet,
        'days_threshold': days_threshold
    }
    
    return {
        'ips': result,
        'stats': stats
    }

def get_free_ips(subnet='172.23.51.0/23', days_threshold=7):
    """Retorna apenas IPs livres ou provavelmente livres"""
    ip_map = get_ip_map(subnet, days_threshold)
    free_ips = [ip for ip in ip_map['ips'] if ip['status'] in ['free', 'probably_free']]
    
    return {
        'free_ips': free_ips,
        'count': len(free_ips),
        'stats': ip_map['stats']
    }

def suggest_next_ip(subnet='172.23.51.0/23', days_threshold=7):
    """Sugere próximo IP livre para uso"""
    free_data = get_free_ips(subnet, days_threshold)
    
    if free_data['free_ips']:
        # Priorizar IPs nunca usados
        never_used = [ip for ip in free_data['free_ips'] if ip['status'] == 'free']
        if never_used:
            return never_used[0]
        else:
            return free_data['free_ips'][0]
    
    return None
