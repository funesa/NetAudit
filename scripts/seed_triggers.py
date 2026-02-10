import sys
import os

# Adicionar diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, get_session
from models import Trigger

def seed_default_triggers():
    init_db()
    session = get_session()
    
    defaults = [
        {
            'name': 'Alta Utilização de CPU',
            'description': 'Processamento acima de 95% por 5 min',
            'metric_type': 'cpu_usage',
            'operator': '>',
            'threshold': 95.0,
            'duration_seconds': 300,
            'severity': 'warning',
            'enabled': True
        },
        {
            'name': 'Memória RAM Crítica',
            'description': 'Uso de memória acima de 90%',
            'metric_type': 'ram_usage',
            'operator': '>',
            'threshold': 90.0,
            'duration_seconds': 60,
            'severity': 'high',
            'enabled': True
        },
        {
            'name': 'Disco Quase Cheio',
            'description': 'Uso de disco acima de 90%',
            'metric_type': 'disk_usage',
            'operator': '>',
            'threshold': 90.0,
            'duration_seconds': 0, 
            'severity': 'average',
            'enabled': True
        },
         {
            'name': 'Latência Alta',
            'description': 'Latência acima de 200ms',
            'metric_type': 'latency',
            'operator': '>',
            'threshold': 200.0,
            'duration_seconds': 60,
            'severity': 'warning',
            'enabled': True
        }
    ]
    
    print("Verificando triggers...")
    
    for t_data in defaults:
        existing = session.query(Trigger).filter(
            Trigger.metric_type == t_data['metric_type'],
            Trigger.name == t_data['name']
        ).first()
        
        if not existing:
            trigger = Trigger(**t_data)
            session.add(trigger)
            print(f"Criado novo trigger: {t_data['name']}")
        else:
            print(f"Trigger já existe: {t_data['name']}")
            
    session.commit()
    session.close()
    print("Seed completo!")

if __name__ == "__main__":
    seed_default_triggers()
