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
