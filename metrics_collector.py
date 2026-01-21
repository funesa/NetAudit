import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime
import psutil

# Importar banco de dados e modelos
from database import get_session
from models import Device, Metric, Alert, Trigger

# Configuração de Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MetricsCollector")

class MetricsCollector:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        
    def start(self):
        """Inicia o agendador de coleta de métricas"""
        if self.is_running:
            return
            
        logger.info("Iniciando Metrics Collector...")
        # Adiciona tarefa para rodar a cada 60 segundos
        self.scheduler.add_job(
            self.collect_all_metrics,
            trigger=IntervalTrigger(seconds=60),
            id='collect_metrics',
            name='Coleta de Métricas Global',
            replace_existing=True
        )
        self.scheduler.start()
        self.is_running = True
        logger.info("Metrics Collector iniciado. Intervalo: 60s")

    def stop(self):
        """Para o agendador"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Metrics Collector parado.")

    def collect_all_metrics(self):
        """Função principal que itera sobre dispositivos e coleta métricas"""
        session = get_session()
        try:
            logger.info(">>> Iniciando ciclo de coleta de métricas...")
            
            # Buscar dispositivos a serem monitorados (ex: todos ou filtrados)
            devices = session.query(Device).all()
            
            for device in devices:
                try:
                    self.collect_device_metrics(session, device)
                except Exception as e:
                    logger.error(f"Erro ao coletar métricas do dispositivo {device.hostname} ({device.ip}): {e}")
            
            session.commit()
            logger.info(">>> Ciclo de coleta finalizado.")
            
        except Exception as e:
            logger.error(f"Erro crítico no ciclo de coleta: {e}")
            session.rollback()
        finally:
            session.close()

    def collect_device_metrics(self, session: Session, device: Device):
        """Coleta métricas de um único dispositivo com base em seu tipo"""
        
        # 1. Monitoramento Local (Auto-monitoramento do Servidor)
        if device.ip in ['127.0.0.1', 'localhost', '0.0.0.0']:
            self._collect_local_metrics(session, device)
            return

        # 2. Monitoramento Remoto (Windows/Linux/Network) - Placeholder
        # Aqui entra a lógica de WMI, SSH ou SNMP
        pass

    def _collect_local_metrics(self, session: Session, device: Device):
        """Coleta métricas da própria máquina usando psutil"""
        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        # Salvar CPU
        metric_cpu = Metric(
            device_id=device.id,
            metric_type='cpu_usage',
            value=cpu_percent,
            unit='%'
        )
        session.add(metric_cpu)
        
        # Salvar RAM
        metric_ram = Metric(
            device_id=device.id,
            metric_type='ram_usage',
            value=ram_percent,
            unit='%'
        )
        session.add(metric_ram)

        # Salvar Disk
        metric_disk = Metric(
            device_id=device.id,
            metric_type='disk_usage',
            value=disk_percent,
            unit='%'
        )
        session.add(metric_disk)
        
        # Verificar Triggers (Simples)
        self._check_triggers(session, device, 'cpu_usage', cpu_percent)
        self._check_triggers(session, device, 'ram_usage', ram_percent)

    def _check_triggers(self, session: Session, device: Device, metric_type: str, value: float):
        """Verifica se alguma regra foi violada"""
        # Buscar triggers ativos para este tipo de métrica
        # Placeholder para lógica real de comparação com a tabela Trigger
        pass

# Instância global
collector = MetricsCollector()
