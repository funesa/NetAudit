import sqlite3
import os
from database import DB_PATH

def migrate_add_permissions():
    print(f"Iniciando migração em: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Banco de dados não encontrado. Nada a migrar.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verifica se a coluna já existe
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'permissions' not in columns:
            print("Adicionando coluna 'permissions' à tabela 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN permissions JSON")
            
            # Define permissões padrão para usuários existentes
            # Admin (role='admin' ou id=1) -> tudo
            # Outros -> view_all
            cursor.execute("UPDATE users SET permissions = '{\"all\": true}' WHERE role = 'admin' OR id = 1")
            cursor.execute("UPDATE users SET permissions = '{\"view_all\": true}' WHERE (role != 'admin' AND id != 1) OR role IS NULL")
            
            conn.commit()
            print("Migração concluída com sucesso!")
        else:
            print("Coluna 'permissions' já existe. Pulando migração.")
            
    except Exception as e:
        print(f"Erro durante a migração: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_add_permissions()
