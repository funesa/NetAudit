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
            CommunityData(community, mpModel=1), # Tenta SNMPv2c
            UdpTransportTarget((ip, 161), timeout=2.5, retries=2),
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
                oid_num = ".".join(map(str, varBind[0].asTuple())) # Ex: 1.3.6.1.2.1.1.1.0
                value = varBind[1].prettyPrint()
                results[oid_num] = value
                
    except Exception as e:
        return {"error": str(e)}
    finally:
        snmpEngine.closeDispatcher()
        
    return results

async def snmp_walk(ip, oid, community='public'):
    """Faz um WALK SNMP para obter uma tabela inteira"""
    results = []
    snmpEngine = SnmpEngine()
    
    try:
        iterator = nextCmd(
            snmpEngine,
            CommunityData(community, mpModel=1),
            UdpTransportTarget((ip, 161), timeout=2.0, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False
        )

        async for errorIndication, errorStatus, errorIndex, varBinds in iterator:
            if errorIndication or errorStatus:
                break
            
            for varBind in varBinds:
                results.append(varBind[1].prettyPrint())
                
    except Exception:
        pass
    finally:
        snmpEngine.closeDispatcher()
        
    return results

def get_printer_data(ip, community='public'):
    """Função wrapper para ser chamada de forma síncrona pelo app.py"""
    # ... (Generic OIDs - Keep existing)
    sys_oids = [
        '1.3.6.1.2.1.1.1.0',            # SysDesc
        '1.3.6.1.2.1.1.3.0',            # SysUpTime
        '1.3.6.1.2.1.1.4.0',            # SysContact
        '1.3.6.1.2.1.1.5.0',            # SysName
        '1.3.6.1.2.1.1.6.0',            # SysLocation
        '1.3.6.1.2.1.43.5.1.1.17.1',    # Serial Number
        '1.3.6.1.2.1.43.10.2.1.4.1.1',  # Total Page Count
        '1.3.6.1.2.1.25.3.5.1.1.1',     # Printer Status
        '1.3.6.1.2.1.25.3.5.1.2.1',     # Error State
        '1.3.6.1.2.1.43.16.5.1.2.1.1',  # Console Display Buffer
    ]
    
    # Supplies OIDs (Keep existing)
    supply_oids = []
    for i in range(1, 21): 
        supply_oids.append(f'1.3.6.1.2.1.43.11.1.1.6.1.{i}') # Name
        supply_oids.append(f'1.3.6.1.2.1.43.11.1.1.8.1.{i}') # Max Capacity
        supply_oids.append(f'1.3.6.1.2.1.43.11.1.1.9.1.{i}') # Current Level
    
    all_get_oids = sys_oids + supply_oids

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 1. SNMP GET (Scalar Data)
        data = loop.run_until_complete(snmp_get(ip, all_get_oids, community))
        
        # 2. SNMP WALKS (Table Data - Best Effort)
        # Alerts & Jobs
        alerts_walk = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.2.1.43.18.1.1.8', community))
        jobs_walk = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.4.1.2699.1.1.1.1.6', community))
        
        # Max Info: Input Trays (Paper)
        tray_names = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.2.1.43.8.2.1.18', community))
        tray_levels = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.2.1.43.8.2.1.10', community))
        tray_caps = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.2.1.43.8.2.1.9', community))
        
        # Max Info: Output Bins
        out_names = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.2.1.43.9.2.1.6', community))
        out_levels = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.2.1.43.9.2.1.5', community)) # Remaining capacity usually
        
        # Max Info: Covers/Doors
        cover_descs = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.2.1.43.6.1.1.2', community))
        cover_status = loop.run_until_complete(snmp_walk(ip, '1.3.6.1.2.1.43.6.1.1.3', community))

        loop.close()
        
        if "error" in data:
            return None

        def clean_snmp_string(s):
            """Filters out garbage SNMP strings"""
            if not s or s == "N/A": return ""
            s = str(s).strip()
            lower = s.lower()
            if "no such" in lower or "nosuch" in lower: return ""
            if "void" in lower: return ""
            if "unknown" in lower: return ""
            return s

        def find_val(oid_suffix):
            for k, v in data.items():
                if k.endswith(oid_suffix): return v
            return "N/A"

        def format_uptime(timeticks):
            try:
                ticks = int(timeticks)
                # Timeticks são centésimos de segundo
                seconds = ticks // 100
                days, remainder = divmod(seconds, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, _ = divmod(remainder, 60)
                if days > 0: return f"{days}d {hours}h {minutes}m"
                return f"{hours}h {minutes}m"
            except: return "N/A"

        # Tenta extrair valores
        sys_name = clean_snmp_string(find_val('1.1.5.0'))
        model = clean_snmp_string(find_val('1.1.1.0'))
        location = clean_snmp_string(find_val('1.1.6.0'))
        contact = clean_snmp_string(find_val('1.1.4.0'))
        serial = clean_snmp_string(find_val('43.5.1.1.17.1'))
        
        # Process Alerts
        alerts_list = []
        if alerts_walk:
            seen_shorts = set()
            for a in alerts_walk:
                a = str(a).strip()
                if a and len(a) > 2 and a not in seen_shorts:
                    alerts_list.append(a)
                    seen_shorts.add(a)

        # Process Job History
        job_history = []
        if jobs_walk:
            from collections import Counter
            job_counts = Counter([str(j).strip() for j in jobs_walk if len(str(j).strip()) > 1])
            job_history = [{"user": k, "count": v} for k, v in job_counts.most_common(5)]

        # Process Trays
        trays = []
        if tray_names:
            for i, name in enumerate(tray_names):
                try:
                    cap = int(tray_caps[i]) if i < len(tray_caps) else -1
                    lvl = int(tray_levels[i]) if i < len(tray_levels) else -1
                    
                    # RFC Printer MIB: -1=No Restriction, -2=Unknown, -3=Some
                    status = "OK"
                    pct = 0
                    if lvl == -3: 
                        status = "Disponível"
                        pct = 100
                    elif lvl >= 0 and cap > 0:
                        pct = int((lvl / cap) * 100)
                        status = f"{pct}%"
                    elif lvl == 0 and cap > 0:
                        status = "Vazia"
                        pct = 0
                    
                    if name:
                        trays.append({
                            "name": str(name),
                            "capacity": cap,
                            "level": lvl,
                            "pct": pct,
                            "status": status
                        })
                except: pass

        # Process Covers/Doors
        covers = []
        if cover_descs:
            for i, desc in enumerate(cover_descs):
                desc_clean = clean_snmp_string(desc)
                if not desc_clean: continue
                try:
                    st = int(cover_status[i]) if i < len(cover_status) else 0
                    st_str = "Desconhecido"
                    is_open = False
                    if st == 3: 
                        st_str = "ABERTA"
                        is_open = True
                    elif st == 4: st_str = "Fechada"
                    elif st == 5: 
                        st_str = "ABERTA (Travada)"
                        is_open = True
                    elif st == 6: st_str = "Fechada (Travada)"
                    
                    covers.append({"name": desc_clean, "status": st_str, "is_open": is_open})
                except: pass

        p_data = {
            "model": model, 
            "hostname": sys_name,
            "location": location,
            "contact": contact,
            "uptime_raw": find_val('1.1.3.0'),
            "uptime": format_uptime(find_val('1.1.3.0')),
            "serial": serial,
            "pages": find_val('43.10.2.1.4.1.1'),
            "status": find_val('25.3.5.1.1.1'),
            "error_state": find_val('25.3.5.1.2.1'),
            "console_display": find_val('43.16.5.1.2.1.1'),
            "supplies": [],
            "alerts": alerts_list,
            "job_history": job_history,
            "trays": trays,
            "covers": covers
        }
        
        # Mapeia suprimentos com lógica RFC 3805
        for i in range(1, 21):
            name = find_val(f'43.11.1.1.6.1.{i}')
            max_cap = find_val(f'43.11.1.1.8.1.{i}')
            level = find_val(f'43.11.1.1.9.1.{i}')
            
            if name != "N/A" and level != "N/A":
                level_display = "-1"
                status_msg = "OK"
                try:
                    lv = int(level)
                    mx = int(max_cap)
                    
                    if lv == -3:
                        level_display = "10" 
                        status_msg = "OK (Algum restante)"
                    elif lv == -2:
                        level_display = "-1"
                        status_msg = "Desconhecido"
                    elif mx > 0:
                        pct = int((lv / mx) * 100)
                        if pct > 100: pct = 100
                        if pct < 0: pct = 0
                        level_display = f"{pct}"
                        status_msg = f"{pct}%"
                    else:
                        level_display = "100" 
                except:
                    level_display = "-1"
                
                name_clean = name.strip()
                if name_clean and name_clean.lower() != "unknown":
                    p_data["supplies"].append({
                        "name": name_clean, 
                        "level": level_display,
                        "status_msg": status_msg
                    })
                
        return p_data
    except Exception as e:
        return None

def get_printer_metrics_for_monitoring(ip, community='public'):
    """
    Função específica para monitoramento - retorna métricas estruturadas
    """
    printer_data = get_printer_data(ip, community)
    
    if not printer_data:
        return None
    
    metrics = {
        'page_count': 0,
        'status': printer_data.get('status', 'unknown'),
        'has_errors': printer_data.get('error_state', '0') != '0',
        'low_toner_supplies': []
    }

    try:
        metrics['page_count'] = int(printer_data.get('pages', 0))
    except: pass
    
    # Processar suprimentos para extrair toner
    for supply in printer_data.get('supplies', []):
        name = supply.get('name', '').lower()
        level_str = supply.get('level', '-1')
        
        try:
            level = int(level_str)
        except:
            level = -1
        
        # Identificar tipo de toner/tinta (Black / Cyan / Magenta / Yellow / K / C / M / Y)
        # Regex simples para cores
        if 'black' in name or 'preto' in name or ' k ' in name or name.endswith(' k'):
            metrics['toner_black'] = level
        elif 'cyan' in name or 'ciano' in name or ' c ' in name or name.endswith(' c'):
            metrics['toner_cyan'] = level
        elif 'magenta' in name or ' m ' in name or name.endswith(' m'):
            metrics['toner_magenta'] = level
        elif 'yellow' in name or 'amarelo' in name or ' y ' in name or name.endswith(' y'):
            metrics['toner_yellow'] = level
        
        # Alertas de toner baixo (< 10%)
        if level != -1 and level < 10:
            metrics['low_toner_supplies'].append(supply.get('name'))
    
    return metrics
