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
    echo=False,  # Set to True para debug SQL
    pool_pre_ping=True,  # Verifica conexões antes de usar
    connect_args={'check_same_thread': False}  # Necessário para SQLite com threads
)

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
