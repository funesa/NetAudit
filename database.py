"""
Configuração do banco de dados SQLAlchemy
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base

# Caminho do banco de dados
DB_PATH = os.path.join(os.getcwd(), 'netaudit.db')
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
