from flask import Blueprint, jsonify, request
from database import get_session
from models import Metric, Device, Alert
from sqlalchemy import desc
from datetime import datetime, timedelta

metrics_bp = Blueprint('metrics_bp', __name__)

@metrics_bp.route('/api/metrics/<int:device_id>', methods=['GET'])
def get_device_metrics(device_id):
    """Retorna as últimas métricas de um dispositivo"""
    session = get_session()
    try:
        # Parâmetros de filtro
        limit = request.args.get('limit', 20, type=int)
        metric_type = request.args.get('type')
        
        query = session.query(Metric).filter(Metric.device_id == device_id)
        
        if metric_type:
            query = query.filter(Metric.metric_type == metric_type)
            
        # Ordenar por mais recente
        metrics = query.order_by(desc(Metric.timestamp)).limit(limit).all()
        
        # Formatar resposta
        data = [{
            'id': m.id,
            'type': m.metric_type,
            'value': m.value,
            'unit': m.unit,
            'timestamp': m.timestamp.isoformat()
        } for m in metrics]
        
        # Inverter para gráfico (cronológico)
        return jsonify({'success': True, 'data': data[::-1]})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@metrics_bp.route('/api/alerts/active', methods=['GET'])
def get_active_alerts():
    """Retorna alertas ativos"""
    session = get_session()
    try:
        alerts = session.query(Alert).filter(Alert.resolved_at == None).order_by(desc(Alert.triggered_at)).all()
        
        data = [{
            'id': a.id,
            'device_id': a.device_id,
            'severity': a.severity,
            'title': a.title,
            'message': a.message,
            'timestamp': a.triggered_at.isoformat()
        } for a in alerts]
        
        return jsonify({'success': True, 'count': len(data), 'alerts': data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@metrics_bp.route('/api/metrics/history', methods=['GET'])
def get_metrics_history():
    """Retorna histórico de métricas agregadas para gráficos (global ou por device)"""
    session = get_session()
    try:
        device_id = request.args.get('device_id', type=int)
        hours = request.args.get('hours', 24, type=int)
        
        since = datetime.now() - timedelta(hours=hours)
        
        query = session.query(Metric).filter(Metric.timestamp >= since)
        if device_id:
            query = query.filter(Metric.device_id == device_id)
            
        metrics = query.order_by(Metric.timestamp).all()
        
        # Agrupar dados por tipo e hora
        history = {
            'labels': [],
            'cpu': [],
            'ram': [],
            'disk': []
        }
        
        # Gerar buckets de hora
        buckets = {}
        for h in range(hours + 1):
            dt = (datetime.now() - timedelta(hours=h)).replace(minute=0, second=0, microsecond=0)
            buckets[dt.isoformat()] = {'cpu': [], 'ram': [], 'disk': []}
            
        for m in metrics:
            bucket_key = m.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
            if bucket_key in buckets:
                m_type = 'cpu' if 'cpu' in m.metric_type else 'ram' if 'ram' in m.metric_type else 'disk' if 'disk' in m.metric_type else None
                if m_type:
                    buckets[bucket_key][m_type].append(m.value)
        
        # Converter buckets em listas ordenadas
        sorted_keys = sorted(buckets.keys())
        for key in sorted_keys:
            history['labels'].append(datetime.fromisoformat(key).strftime('%H:00'))
            
            # Média das métricas no bucket
            vals = buckets[key]
            history['cpu'].append(round(sum(vals['cpu']) / len(vals['cpu']), 1) if vals['cpu'] else 0)
            history['ram'].append(round(sum(vals['ram']) / len(vals['ram']), 1) if vals['ram'] else 0)
            history['disk'].append(round(sum(vals['disk']) / len(vals['disk']), 1) if vals['disk'] else 0)
            
        return jsonify(history)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@metrics_bp.route('/api/monitoring/processes', methods=['GET'])
def get_device_processes():
    """Retorna os top processos de um dispositivo do cache do collector"""
    from metrics_collector import collector
    from database import get_session
    from models import Device
    
    device_id = request.args.get('device_id', type=int)
    
    # Se não passar ID, tenta achar o localhost (127.0.0.1)
    if not device_id:
        session = get_session()
        try:
            local_device = session.query(Device).filter(Device.ip == '127.0.0.1').first()
            if local_device:
                device_id = local_device.id
        finally:
            session.close()
            
    if not device_id:
        return jsonify({'success': False, 'message': 'Dispositivo não encontrado'}), 404
        
    processes = collector.process_cache.get(device_id, [])
    
    return jsonify({
        'success': True,
        'device_id': device_id,
        'processes': processes
    })
