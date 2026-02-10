import sys
import os
import time
from datetime import datetime

# Adicionar diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_session
from models import Alert, Device

def create_test_alert():
    session = get_session()
    
    # Pegar um device qualquer
    device = session.query(Device).first()
    if not device:
        print("Nenhum dispositivo encontrado. Rode o sistema primeiro.")
        return

    print("Criando alerta de teste...")
    alert = Alert(
        device_id=device.id,
        severity='high',
        title="TESTE DE ALERTA DO SISTEMA",
        message="[SERVIDOR-01] Esta é uma notificação de teste. Se você está vendo isso, o sistema Zabbix-like está funcionando!",
        triggered_at=datetime.now()
    )
    session.add(alert)
    session.commit()
    print(f"Alerta criado! ID: {alert.id}")
    print("Verifique o frontend agora. O alerta deve aparecer em vermelho.")
    
    # Esperar 20 segundos
    print("Aguardando 20 segundos antes de resolver...")
    time.sleep(20)
    
    # Resolver
    alert.resolved_at = datetime.now()
    session.commit()
    print("Alerta resolvido! Deve desaparecer do frontend.")
    session.close()

if __name__ == "__main__":
    create_test_alert()
