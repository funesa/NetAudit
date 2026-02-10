"""
Alert Manager - Gerenciamento centralizado de alertas
Responsável por criar, resolver e gerenciar alertas do sistema
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Alert, Trigger, Device
from database import get_session

logger = logging.getLogger("AlertManager")


class AlertManager:
    """Gerenciador centralizado de alertas"""
    
    def __init__(self):
        self.active_violations = {}  # Track de violações ativas para triggers com duração
        
    def create_alert(self, device_id, trigger, current_value, session=None):
        """
        Cria novo alerta se não existir um ativo para o mesmo trigger+device
        
        Args:
            device_id: ID do dispositivo
            trigger: Objeto Trigger que foi violado
            current_value: Valor atual da métrica que violou o trigger
            session: Sessão do banco (opcional, cria uma nova se não fornecida)
            
        Returns:
            Alert: Alerta criado ou None se já existe
        """
        own_session = session is None
        if own_session:
            session = get_session()
            
        try:
            # Verificar se já existe alerta ativo para este trigger+device
            existing_alert = session.query(Alert).filter(
                Alert.device_id == device_id,
                Alert.title == trigger.name,
                Alert.resolved_at == None
            ).first()
            
            if existing_alert:
                logger.debug(f"Alerta já existe para {trigger.name} no device {device_id}")
                return None
            
            # Buscar Device para obter hostname
            device = session.query(Device).filter(Device.id == device_id).first()
            hostname = device.hostname if device else "Unknown Device"

            # Criar mensagem descritiva
            message = self._format_alert_message(trigger, current_value, hostname)
            
            # Criar novo alerta
            alert = Alert(
                device_id=device_id,
                severity=trigger.severity,
                title=trigger.name,
                message=message,
                triggered_at=datetime.now()
            )
            
            session.add(alert)
            if own_session:
                session.commit()
                
            logger.info(f"✅ Alerta criado: {trigger.name} para device {device_id} (valor: {current_value})")
            
            # Processar notificações se configurado
            if trigger.notify_email or trigger.notify_webhook:
                self._send_notifications(alert, trigger)
            
            return alert
            
        except Exception as e:
            logger.error(f"Erro ao criar alerta: {e}")
            if own_session:
                session.rollback()
            return None
        finally:
            if own_session:
                session.close()
    
    def auto_resolve_alerts(self, device_id, metric_type, current_value, session=None):
        """
        Resolve automaticamente alertas quando a condição normaliza
        
        Args:
            device_id: ID do dispositivo
            metric_type: Tipo de métrica (cpu_usage, ram_usage, etc)
            current_value: Valor atual da métrica
            session: Sessão do banco (opcional)
        """
        own_session = session is None
        if own_session:
            session = get_session()
            
        try:
            # Buscar alertas ativos relacionados a esta métrica
            active_alerts = session.query(Alert).join(Device).filter(
                Alert.device_id == device_id,
                Alert.resolved_at == None
            ).all()
            
            for alert in active_alerts:
                # Buscar trigger correspondente
                trigger = session.query(Trigger).filter(
                    Trigger.name == alert.title,
                    Trigger.metric_type == metric_type
                ).first()
                
                if not trigger:
                    continue
                
                # Verificar se condição não é mais violada
                condition_ok = self._check_condition_ok(trigger, current_value)
                
                if condition_ok:
                    alert.resolved_at = datetime.now()
                    if own_session:
                        session.commit()
                    logger.info(f"✅ Alerta auto-resolvido: {alert.title} para device {device_id}")
                    
        except Exception as e:
            logger.error(f"Erro ao auto-resolver alertas: {e}")
            if own_session:
                session.rollback()
        finally:
            if own_session:
                session.close()
    
    def acknowledge_alert(self, alert_id, username, session=None):
        """
        Marca alerta como reconhecido (acknowledged)
        
        Args:
            alert_id: ID do alerta
            username: Usuário que reconheceu
            session: Sessão do banco (opcional)
            
        Returns:
            bool: True se sucesso
        """
        own_session = session is None
        if own_session:
            session = get_session()
            
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            
            if not alert:
                return False
            
            alert.acknowledged = True
            alert.acknowledged_by = username
            alert.acknowledged_at = datetime.now()
            
            if own_session:
                session.commit()
                
            logger.info(f"Alerta {alert_id} reconhecido por {username}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao reconhecer alerta: {e}")
            if own_session:
                session.rollback()
            return False
        finally:
            if own_session:
                session.close()
    
    def check_trigger_violation(self, device_id, trigger, current_value, session=None):
        """
        Verifica se um trigger foi violado considerando duração mínima
        
        Args:
            device_id: ID do dispositivo
            trigger: Objeto Trigger
            current_value: Valor atual da métrica
            session: Sessão do banco
            
        Returns:
            bool: True se deve criar alerta
        """
        # Chave única para rastrear violação
        violation_key = f"{device_id}_{trigger.id}"
        
        # Verificar se condição está violada
        is_violated = self._evaluate_condition(trigger, current_value)
        
        if not is_violated:
            # Limpar rastreamento se existir
            if violation_key in self.active_violations:
                del self.active_violations[violation_key]
            return False
        
        # Duração mínima configurada
        if trigger.duration_seconds and trigger.duration_seconds > 0:
            now = datetime.now()
            
            if violation_key not in self.active_violations:
                # Primeira violação - iniciar rastreamento
                self.active_violations[violation_key] = now
                return False
            else:
                # Verificar se duração foi atingida
                first_violation_time = self.active_violations[violation_key]
                duration = (now - first_violation_time).total_seconds()
                
                if duration >= trigger.duration_seconds:
                    # Duração atingida - criar alerta
                    return True
                else:
                    return False
        else:
            # Sem duração mínima - criar alerta imediatamente
            return True
    
    def _evaluate_condition(self, trigger, current_value):
        """Avalia se condição do trigger está violada"""
        if current_value is None:
            return False
            
        operator = trigger.operator
        threshold = trigger.threshold
        
        if operator == '>':
            return current_value > threshold
        elif operator == '>=':
            return current_value >= threshold
        elif operator == '<':
            return current_value < threshold
        elif operator == '<=':
            return current_value <= threshold
        elif operator == '==':
            return current_value == threshold
        else:
            return False
    
    def _check_condition_ok(self, trigger, current_value):
        """Verifica se condição está OK (inverso da violação)"""
        return not self._evaluate_condition(trigger, current_value)
    
    def _format_alert_message(self, trigger, current_value, hostname="Device"):
        """Formata mensagem do alerta"""
        return f"[{hostname}] {trigger.description or trigger.name}: Valor atual é {current_value}{trigger.metric_type}, threshold: {trigger.operator} {trigger.threshold}"
    
    def _send_notifications(self, alert, trigger):
        """Envia notificações configuradas (placeholder para futura implementação)"""
        # TODO: Implementar sistema de notificações real
        logger.info(f"📧 Notificação deveria ser enviada para alerta: {alert.title}")
        pass
    
    def get_active_alerts_count(self, session=None):
        """
        Retorna contagem de alertas ativos por severidade
        
        Returns:
            dict: {'disaster': 2, 'high': 5, 'average': 10, 'warning': 3, 'info': 1}
        """
        own_session = session is None
        if own_session:
            session = get_session()
            
        try:
            active_alerts = session.query(Alert).filter(Alert.resolved_at == None).all()
            
            counts = {
                'disaster': 0,
                'high': 0,
                'average': 0,
                'warning': 0,
                'info': 0
            }
            
            for alert in active_alerts:
                if alert.severity in counts:
                    counts[alert.severity] += 1
            
            counts['total'] = len(active_alerts)
            return counts
            
        finally:
            if own_session:
                session.close()


# Instância global
alert_manager = AlertManager()
