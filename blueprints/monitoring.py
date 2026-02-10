from flask import Blueprint, jsonify, render_template
from core.decorators import login_required, premium_required
from database import get_session
from models import Device, Alert, Metric
from sqlalchemy import desc, func
from alert_manager import alert_manager
from utils import logger

monitoring_bp = Blueprint('monitoring', __name__)

@monitoring_bp.route('/monitoring')
@login_required
def monitoring_page():
    return render_template('monitoring.html')

@monitoring_bp.route('/api/monitoring/overview')
@login_required
def api_monitoring_overview():
    session_db = get_session()
    try:
        total_devices = session_db.query(Device).count()
        alert_counts = alert_manager.get_active_alerts_count(session_db)
        
        devices_with_alerts = session_db.query(Device).join(Alert).filter(
            Alert.resolved_at == None
        ).distinct().count()
        
        def get_top_assets(metric_type, limit=5):
            if metric_type == 'disk_usage':
                latest_ids = session_db.query(
                    func.max(Metric.id)
                ).filter(
                    (Metric.metric_type == 'disk_usage') | (Metric.metric_type.like('disk_usage_%'))
                ).group_by(Metric.device_id).subquery()
            else:
                latest_ids = session_db.query(
                    func.max(Metric.id)
                ).filter(Metric.metric_type == metric_type).group_by(Metric.device_id).subquery()
            
            top_metrics = session_db.query(Metric, Device).join(
                Device, Metric.device_id == Device.id
            ).filter(Metric.id.in_(latest_ids)).order_by(desc(Metric.value)).limit(limit).all()
            
            return [{
                'hostname': d.hostname or d.ip,
                'value': m.value,
                'ip': d.ip
            } for m, d in top_metrics]

        return jsonify({
            'total_devices': total_devices,
            'healthy_devices': total_devices - devices_with_alerts,
            'warning_devices': devices_with_alerts,
            'active_alerts': alert_counts.get('total', 0),
            'rankings': {
                'cpu': get_top_assets('cpu_usage'),
                'ram': get_top_assets('ram_usage'),
                'disk': get_top_assets('disk_usage'),
                'latency': get_top_assets('latency')
            }
        })
    except Exception as e:
        logger.error(f"Erro no Sentinel Overview: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session_db.close()

# More monitoring routes can be moved here...
