"""
Modelos de banco de dados SQLAlchemy para NetAudit System
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Device(Base):
    """Dispositivos da rede"""
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    ip = Column(String(45), unique=True, index=True, nullable=False)
    hostname = Column(String(255))
    device_type = Column(String(50))  # windows, server, printer, network, etc
    icon = Column(String(50))
    vendor = Column(String(100))
    mac = Column(String(17))
    
    # Informações do sistema
    os_detail = Column(String(255))
    model = Column(String(255))
    user = Column(String(255))
    ram = Column(String(50))
    cpu = Column(Text)
    uptime = Column(String(100))
    bios = Column(String(255))
    
    # Dados adicionais (JSON para flexibilidade)
    shares = Column(JSON)
    disks = Column(JSON)
    nics = Column(JSON)
    services = Column(JSON)
    errors = Column(JSON)
    printer_data = Column(JSON)
    
    # Metadados
    confidence = Column(String(50))
    last_seen = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relacionamentos
    metrics = relationship("Metric", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Device(ip='{self.ip}', hostname='{self.hostname}', type='{self.device_type}')>"


class Metric(Base):
    """Métricas de monitoramento em tempo real"""
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False, index=True)
    
    metric_type = Column(String(50), nullable=False, index=True)  # cpu, ram, disk, latency
    value = Column(Float, nullable=False)
    unit = Column(String(20))  # %, GB, ms, etc
    
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    # Relacionamento
    device = relationship("Device", back_populates="metrics")
    
    def __repr__(self):
        return f"<Metric(device_id={self.device_id}, type='{self.metric_type}', value={self.value})>"


class Alert(Base):
    """Alertas e notificações"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False, index=True)
    
    severity = Column(String(20), nullable=False, index=True)  # info, warning, average, high, disaster
    title = Column(String(255), nullable=False)
    message = Column(Text)
    
    triggered_at = Column(DateTime, default=datetime.now, index=True)
    resolved_at = Column(DateTime, nullable=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Relacionamento
    device = relationship("Device", back_populates="alerts")
    
    @property
    def is_active(self):
        return self.resolved_at is None
    
    def __repr__(self):
        return f"<Alert(device_id={self.device_id}, severity='{self.severity}', active={self.is_active})>"


class Trigger(Base):
    """Configuração de triggers para alertas"""
    __tablename__ = 'triggers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Condições
    metric_type = Column(String(50), nullable=False)  # cpu, ram, disk
    operator = Column(String(10), nullable=False)  # >, <, >=, <=, ==
    threshold = Column(Float, nullable=False)
    duration_seconds = Column(Integer, default=300)  # Tempo que a condição deve persistir
    
    # Ação
    severity = Column(String(20), nullable=False)
    notify_email = Column(Boolean, default=True)
    notify_webhook = Column(Boolean, default=False)
    
    # Filtros (opcional - aplicar a dispositivos específicos)
    device_type_filter = Column(String(50))  # Ex: "server" para aplicar só a servidores
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Trigger(name='{self.name}', {self.metric_type} {self.operator} {self.threshold})>"


class MonitoringTemplate(Base):
    """Templates de monitoramento por tipo de dispositivo"""
    __tablename__ = 'monitoring_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    device_type = Column(String(50), nullable=False)  # windows, server, printer, network
    description = Column(Text)
    
    # Configuração (JSON com métricas e triggers)
    config = Column(JSON, nullable=False)
    # Exemplo: {"metrics": ["cpu", "ram", "disk"], "triggers": [...]}
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<MonitoringTemplate(name='{self.name}', type='{self.device_type}')>"
