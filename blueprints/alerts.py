from flask import Blueprint, jsonify, request, session
from database import get_session
from models import Alert
from alert_manager import alert_manager
import logging

# Configuração de Logger
logger = logging.getLogger("AlertsAPI")

# Definição do Blueprint
alerts_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')

@alerts_bp.route('/active', methods=['GET'])
def get_active_alerts():
    """
    Retorna todos os alertas ativos (não resolvidos)
    """
    db_session = get_session()
    try:
        # Buscar alertas não resolvidos com informações do device
        from models import Device
        alerts = db_session.query(Alert).join(Device).filter(Alert.resolved_at == None).all()
        
        result = []
        for alert in alerts:
            result.append({
                'id': alert.id,
                'device_id': alert.device_id,
                'hostname': alert.device.hostname if alert.device else 'Unknown',
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None,
                'acknowledged': alert.acknowledged,
                'monitor_type': 'system' # Flag para distinguir de outras notificações
            })
            
        return jsonify(result)
    except Exception as e:
        logger.error(f"Erro ao buscar alertas ativos: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()

@alerts_bp.route('/<int:alert_id>/ack', methods=['POST'])
def acknowledge_alert(alert_id):
    """
    Reconhece um alerta
    """
    username = session.get('user', 'system_user')
    success = alert_manager.acknowledge_alert(alert_id, username)
    
    if success:
        return jsonify({'message': 'Alerta reconhecido com sucesso'})
    else:
        return jsonify({'error': 'Falha ao reconhecer alerta (não encontrado ou erro interno)'}), 404

@alerts_bp.route('/count', methods=['GET'])
def get_alerts_count():
    """
    Retorna contagem de alertas por severidade
    """
    counts = alert_manager.get_active_alerts_count()
    return jsonify(counts)
