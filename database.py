"""
Configuração do banco de dados SQLAlchemy
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base

# Caminho do banco de dados
from utils import get_data_path
DB_PATH = get_data_path('netaudit.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'

# Criar engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    connect_args={'check_same_thread': False, 'timeout': 30}
)

# Habilitar modo WAL para concorrência
from sqlalchemy import event
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

# Session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_db():
    """Inicializa o banco de dados criando todas as tabelas"""
    Base.metadata.create_all(engine)
    print(f"✅ Banco de dados inicializado: {DB_PATH}")

def get_session():
    """Retorna uma sessão do banco de dados"""
    return Session()

def close_session():
    """Fecha a sessão atual"""
    Session.remove()

def load_all_devices():
    """Carrega todos os dispositivos do banco e formata para o formato NetAudit"""
    from models import Device
    from datetime import datetime, timedelta
    session = get_session()
    try:
        devices = session.query(Device).all()
        results = []
        now = datetime.now()
        for d in devices:
            # Determina status_code: ONLINE se visto nos últimos 15 min
            status = "OFFLINE"
            if d.last_seen:
                diff = (now - d.last_seen).total_seconds()
                if diff < 3600:
                    status = "ONLINE"
                # print(f"DEBUG DB: {d.hostname} - last_seen: {d.last_seen}, diff: {diff}, status: {status}")
            
            results.append({
                'id': d.id,
                'ip': d.ip,
                'hostname': d.hostname or 'N/A',
                'device_type': d.device_type or 'network',
                'status_code': status,
                'icon': d.icon or 'ph-globe',
                'vendor': d.vendor or 'Unknown',
                'mac': d.mac or '-',
                'os_detail': d.os_detail or 'N/A',
                'model': d.model or 'N/A',
                'user': d.user or 'N/A',
                'ram': d.ram or 'N/A',
                'cpu': d.cpu or 'N/A',
                'uptime': d.uptime or 'N/A',
                'bios': d.bios or 'N/A',
                'shares': d.shares or [],
                'disks': d.disks or [],
                'nics': d.nics or [],
                'services': d.services or [],
                'errors': d.errors or [],
                'printer_data': d.printer_data,
                'confidence': d.confidence or 'Baixa',
                'last_seen': d.last_seen.isoformat() if d.last_seen else None
            })
        return results
    except Exception as e:
        print(f"[DB ERROR] Falha ao carregar dispositivos: {e}")
        return []
    finally:
        session.close()
