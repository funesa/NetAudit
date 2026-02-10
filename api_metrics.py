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
    """Retorna histórico de métricas agregadas via Raw SQL para performance máxima"""
    import sqlite3
    from database import DB_PATH
    
    try:
        hours = request.args.get('hours', 24, type=int)
        since = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Conexão direta veloz
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout = 5000")
        cursor = conn.cursor()
        
        # Query otimizada usando o novo índice
        # Agrupamos por data/hora para o gráfico global
        sql = """
            SELECT 
                strftime('%Y-%m-%d %H:00', timestamp) as hour_bucket,
                metric_type,
                AVG(value)
            FROM metrics
            WHERE timestamp >= ? 
              AND (metric_type = 'cpu_usage' OR metric_type = 'ram_usage' OR metric_type LIKE 'disk_usage%')
            GROUP BY hour_bucket, metric_type
            ORDER BY hour_bucket ASC
        """
        cursor.execute(sql, (since,))
        rows = cursor.fetchall()
        conn.close()
        
        # Estrutura para o Recharts
        # { '2023-01-01 10:00': { time: '10:00', cpu: 0, ram: 0, disk: 0 } }
        buckets = {}
        for hour_bucket, m_type, m_val in rows:
            display_time = hour_bucket.split(' ')[1] # Pega apenas o HH:00
            
            if hour_bucket not in buckets:
                buckets[hour_bucket] = {'time': display_time, 'cpu': 0, 'ram': 0, 'disk': 0}
            
            val = round(m_val, 1)
            if m_type == 'cpu_usage':
                buckets[hour_bucket]['cpu'] = val
            elif m_type == 'ram_usage':
                buckets[hour_bucket]['ram'] = val
            elif m_type.startswith('disk_usage'):
                # Média entre diferentes discos/partições para o gráfico global
                if buckets[hour_bucket]['disk'] == 0:
                    buckets[hour_bucket]['disk'] = val
                else:
                    buckets[hour_bucket]['disk'] = round((buckets[hour_bucket]['disk'] + val) / 2, 1)

        # Converter para lista ordenada
        sorted_keys = sorted(buckets.keys())
        sorted_data = [buckets[k] for k in sorted_keys]
        
        if not sorted_data:
            print(f"DEBUG: No metrics found in range {since}")
        
        return jsonify({'success': True, 'data': sorted_data})
        
    except Exception as e:
        import traceback
        print(f"DEBUG ERROR metrics_history: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})

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
