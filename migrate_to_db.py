"""
Script de migração de dados JSON para SQLite
Migra scan_history.json para o banco de dados relacional
"""
import json
import os
from datetime import datetime
from database import init_db, get_session
from models import Device

def migrate_scan_history():
    """Migra dados de scan_history.json para o banco SQLite"""
    
    # Inicializar banco de dados
    print("🔧 Inicializando banco de dados...")
    init_db()
    
    # Carregar dados JSON
    json_file = 'scan_history.json'
    if not os.path.exists(json_file):
        print(f"❌ Arquivo {json_file} não encontrado!")
        return
    
    print(f"📂 Carregando dados de {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Garantir que é uma lista
    if isinstance(data, dict):
        data = list(data.values())
    
    print(f"📊 Encontrados {len(data)} dispositivos para migrar")
    
    # Obter sessão
    session = get_session()
    
    try:
        migrated = 0
        skipped = 0
        errors = 0
        
        for device_data in data:
            try:
                # Verificar se dispositivo já existe
                existing = session.query(Device).filter_by(ip=device_data['ip']).first()
                
                if existing:
                    print(f"⏭️  Dispositivo {device_data['ip']} já existe, pulando...")
                    skipped += 1
                    continue
                
                # Criar novo dispositivo
                device = Device(
                    ip=device_data.get('ip'),
                    hostname=device_data.get('hostname', 'N/A'),
                    device_type=device_data.get('device_type', 'network'),
                    icon=device_data.get('icon', 'ph-globe'),
                    vendor=device_data.get('vendor', 'Unknown'),
                    mac=device_data.get('mac', '-'),
                    os_detail=device_data.get('os_detail', 'N/A'),
                    model=device_data.get('model', 'N/A'),
                    user=device_data.get('user', 'N/A'),
                    ram=device_data.get('ram', 'N/A'),
                    cpu=device_data.get('cpu', 'N/A'),
                    uptime=device_data.get('uptime', 'N/A'),
                    bios=device_data.get('bios', 'N/A'),
                    shares=device_data.get('shares', []),
                    disks=device_data.get('disks', []),
                    nics=device_data.get('nics', []),
                    services=device_data.get('services', []),
                    errors=device_data.get('errors', []),
                    printer_data=device_data.get('printer_data'),
                    confidence=device_data.get('confidence', 'Baixa'),
                    last_seen=datetime.now()
                )
                
                session.add(device)
                migrated += 1
                
                if migrated % 10 == 0:
                    print(f"✅ Migrados {migrated} dispositivos...")
                    session.commit()  # Commit parcial a cada 10
                
            except Exception as e:
                print(f"❌ Erro ao migrar {device_data.get('ip', 'unknown')}: {str(e)}")
                errors += 1
                continue
        
        # Commit final
        session.commit()
        
        print("\n" + "="*50)
        print("✅ Migração concluída!")
        print(f"📊 Estatísticas:")
        print(f"   - Migrados: {migrated}")
        print(f"   - Pulados (já existiam): {skipped}")
        print(f"   - Erros: {errors}")
        print(f"   - Total: {len(data)}")
        print("="*50)
        
        # Criar backup do JSON
        backup_file = f"{json_file}.migrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(json_file, backup_file)
        print(f"💾 Backup criado: {backup_file}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erro durante migração: {str(e)}")
        raise
    finally:
        session.close()

def verify_migration():
    """Verifica a integridade dos dados migrados"""
    print("\n🔍 Verificando migração...")
    
    session = get_session()
    try:
        total_devices = session.query(Device).count()
        print(f"✅ Total de dispositivos no banco: {total_devices}")
        
        # Mostrar alguns exemplos
        sample_devices = session.query(Device).limit(5).all()
        print("\n📋 Amostra de dispositivos:")
        for device in sample_devices:
            print(f"   - {device.ip} | {device.hostname} | {device.device_type}")
        
        return True
    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")
        return False
    finally:
        session.close()

if __name__ == '__main__':
    print("🚀 Iniciando migração de dados...")
    print("="*50)
    
    try:
        migrate_scan_history()
        verify_migration()
        print("\n✅ Processo concluído com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro fatal: {str(e)}")
        exit(1)
