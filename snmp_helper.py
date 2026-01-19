import asyncio
from pysnmp.hlapi.asyncio import *

async def snmp_get(ip, oids, community='public'):
    """Faz um GET SNMP síncrono (embebido em async) para vários OIDs"""
    results = {}
    snmpEngine = SnmpEngine()
    
    # Prepara a lista de objetos de consulta
    object_types = [ObjectType(ObjectIdentity(oid)) for oid in oids]
    
    try:
        # Pysnmp 6.x async API (camelCase)
        iterator = getCmd(
            snmpEngine,
            CommunityData(community),
            UdpTransportTarget((ip, 161), timeout=2, retries=1),
            ContextData(),
            *object_types
        )
        
        errorIndication, errorStatus, errorIndex, varBinds = await iterator
        
        if errorIndication:
            return {"error": str(errorIndication)}
        elif errorStatus:
            return {"error": f"{errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex)-1][0] or '?'}"}
        else:
            for varBind in varBinds:
                # Armazena tanto o OID numérico quanto o "pretty name"
                oid_full = varBind[0].prettyPrint() # Ex: SNMPv2-MIB::sysDescr.0
                oid_num = ".".join(map(str, varBind[0].asTuple())) # Ex: 1.3.6.1.2.1.1.1.0
                value = varBind[1].prettyPrint()
                
                results[oid_full] = value
                results[oid_num] = value
                
    except Exception as e:
        return {"error": str(e)}
    finally:
        snmpEngine.closeDispatcher()
        
    return results

def get_printer_data(ip, community='public'):
    """Função wrapper para ser chamada de forma síncrona pelo app.py"""
    oids = [
        '1.3.6.1.2.1.1.1.0',           # SysDesc
        '1.3.6.1.2.1.43.5.1.1.17.1',    # Serial Number
        '1.3.6.1.2.1.43.10.2.1.4.1.1',  # Total Page Count
        '1.3.6.1.2.1.25.3.5.1.1.1',     # Printer Status
        '1.3.6.1.2.1.25.3.5.1.2.1',     # Error State
    ]
    # Adiciona OIDs de suprimentos dinamicamente
    for i in range(1, 10): # Aumentado para pegar mais itens
        oids.append(f'1.3.6.1.2.1.43.11.1.1.6.1.{i}') # Name
        oids.append(f'1.3.6.1.2.1.43.11.1.1.8.1.{i}') # Max Capacity
        oids.append(f'1.3.6.1.2.1.43.11.1.1.9.1.{i}') # Current Level
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(snmp_get(ip, oids, community))
        loop.close()
        
        if "error" in data:
            return None

        def find_val(oid_suffix):
            for k, v in data.items():
                if k.endswith(oid_suffix): return v
            return "N/A"

        p_data = {
            "model": find_val('1.1.1.0'),
            "serial": find_val('43.5.1.1.17.1'),
            "pages": find_val('43.10.2.1.4.1.1'),
            "status": find_val('25.3.5.1.1.1'),
            "error_state": find_val('25.3.5.1.2.1'),
            "supplies": []
        }
        
        # Mapeia suprimentos
        for i in range(1, 10):
            name = find_val(f'43.11.1.1.6.1.{i}')
            max_cap = find_val(f'43.11.1.1.8.1.{i}')
            level = find_val(f'43.11.1.1.9.1.{i}')
            
            if name != "N/A" and level != "N/A":
                try:
                    lv = int(level)
                    mx = int(max_cap)
                    if mx > 0:
                        pct = int((lv / mx) * 100)
                        level_display = f"{pct}" # Retorna apenas o número para o JS tratar
                    else:
                        level_display = "-1" # Interpretado como "OK" ou "Incalculável"
                except:
                    level_display = "-1"
                
                p_data["supplies"].append({"name": name, "level": level_display})
                
        return p_data
    except Exception as e:
        print(f"Erro SNMP para {ip}: {e}")
        return None
