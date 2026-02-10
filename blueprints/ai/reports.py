import datetime
import time
import re
from flask import jsonify
from ad_helper import get_ad_storage, get_failed_logins
from blueprints.ai.utils import load_scan_data

def generate_report_logic(command_norm):
    # 1. Identifica o tipo de relatório e threshold
    threshold = 10 # Default %
    match = re.search(r'(\d+)\s*%', command_norm)
    if match: threshold = int(match.group(1))
    
    type_rep = "disk" # Default
    if "cpu" in command_norm: type_rep = "cpu"
    elif "seguranca" in command_norm or "logins" in command_norm or "falhas" in command_norm: type_rep = "security"
    elif "inventario" in command_norm or "ativos" in command_norm or "parque" in command_norm or "so" in command_norm:
        if "completo" in command_norm or "lista" in command_norm or "todos" in command_norm or "detalhado" in command_norm:
            type_rep = "full_inventory"
        else:
            type_rep = "inventory"
    
    if type_rep == "disk":
        storage = get_ad_storage()
        if not storage: return jsonify({'description': 'Não consegui obter dados de armazenamento dos servidores.'})
        
        alerts = []
        for d in storage:
            try:
                pct_used = float(d.get('PctUsed', 0))
                free_pct = 100 - pct_used
                if free_pct < threshold:
                    alerts.append(d)
            except: continue
            
        if not alerts:
            return jsonify({'description': f'Tudo certo! Nenhum servidor está com menos de {threshold}% de disco livre.'})
            
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        report_id = f"report_{int(time.time())}"
        
        html = f"""
        <div id="{report_id}" style="background:white; color:black; padding:20px; border-radius:8px; font-family:sans-serif;">
            <div style="border-bottom:2px solid #ddd; padding-bottom:10px; margin-bottom:15px; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="margin:0; font-size:18px;">Relatório de Capacidade de Servidores</h2>
                <span style="font-size:12px; color:#666;">Gerado em: {now_str}</span>
            </div>
            <p style="font-size:12px; margin-bottom:15px;">Filtro: Espaço Livre < <strong>{threshold}%</strong></p>
            
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <tr style="background:#f3f4f6; text-align:left;">
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Servidor</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Disco</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Total</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Livre (GB)</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Livre (%)</th>
                </tr>
        """
        
        for a in alerts:
            total = float(a.get('TotalGB', 0))
            free = float(a.get('FreeGB', 0))
            pct = round((free / total) * 100, 1) if total > 0 else 0
            color = "#dc2626" if pct < 5 else "#ea580c"
            
            html += f"""
                <tr>
                    <td style="padding:8px; border-bottom:1px solid #eee;">{a.get('Server', 'Unknown')}</td>
                    <td style="padding:8px; border-bottom:1px solid #eee;">{a.get('Drive', '-')} ({a.get('Label', '')})</td>
                    <td style="padding:8px; border-bottom:1px solid #eee;">{a.get('TotalGB', 0)} GB</td>
                    <td style="padding:8px; border-bottom:1px solid #eee;">{a.get('FreeGB', 0)} GB</td>
                    <td style="padding:8px; border-bottom:1px solid #eee; font-weight:bold; color:{color};">{pct}%</td>
                </tr>
            """
            
        html += f"""
            </table>
            <div style="margin-top:20px; text-align:center; font-size:10px; color:#999;">
                Atena AI Analysis • SCAN 2026
            </div>
        </div>
        <div style="margin-top:10px; text-align:right;">
            <button onclick="window.printAtenaReport('{report_id}')" style="background:#2563eb; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold;">Imprimir / Salvar PDF</button>
        </div>
        """
        return jsonify({'description': f'Relatório gerado com <strong>{len(alerts)} alertas</strong>:<br><br>{html}'}) 

    elif type_rep == "security":
        hours = 24
        if "48" in command_norm: hours = 48
        if "72" in command_norm: hours = 72
        
        failures = get_failed_logins(hours=hours)
        if not failures: return jsonify({'description': f'Nenhuma falha de login detectada nas últimas {hours} horas.'})
        
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        report_id = f"report_sec_{int(time.time())}"
        
        html = f"""
        <div id="{report_id}" style="background:white; color:black; padding:20px; border-radius:8px; font-family:sans-serif;">
            <div style="border-bottom:2px solid #ddd; padding-bottom:10px; margin-bottom:15px; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="margin:0; font-size:18px;">Relatório de Segurança: Falhas de Login</h2>
                <span style="font-size:12px; color:#666;">Gerado em: {now_str}</span>
            </div>
            <p style="font-size:12px; margin-bottom:15px;">Período analisado: Últimas <strong>{hours} horas</strong> ({len(failures)} eventos)</p>
            
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <tr style="background:#f3f4f6; text-align:left;">
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Horário</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Usuário</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Origem (IP/Host)</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Status/Erro</th>
                </tr>
        """
        
        for f in failures[:50]:
            html += f"""
                <tr>
                    <td style="padding:8px; border-bottom:1px solid #eee;">{f.get('TimeGenerated', 'N/A')}</td>
                    <td style="padding:8px; border-bottom:1px solid #eee; font-weight:bold;">{f.get('TargetUser', 'Unknown')}</td>
                    <td style="padding:8px; border-bottom:1px solid #eee;">{f.get('IpAddress', '-')}<br><span style="color:#666; font-size:9px;">{f.get('WorkstationName', '-')}</span></td>
                    <td style="padding:8px; border-bottom:1px solid #eee; color:#dc2626;">{f.get('Status', 'Falha Genérica')}</td>
                </tr>
            """
        
        html += f"""
            </table>
            <div style="margin-top:20px; text-align:center; font-size:10px; color:#999;">
                Atena Security Analysis • SCAN 2026
            </div>
        </div>
        <div style="margin-top:10px; text-align:right;">
            <button onclick="window.printAtenaReport('{report_id}')" style="background:#2563eb; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold;">Imprimir / Salvar PDF</button>
        </div>
        """
        return jsonify({'description': f'Relatório de segurança gerado com <strong>{len(failures)} eventos</strong>:<br><br>{html}'})

    elif type_rep == "inventory":
        assets = load_scan_data()
        if not assets: return jsonify({'description': 'Nenhum dado de inventário (Scan) disponível.'})
        
        total_assets = len(assets)
        by_os = {}
        online_count = 0
        
        for a in assets:
            os_name = a.get('os_detail') or a.get('os') or 'Desconhecido'
            if 'Windows 10' in os_name: os_group = 'Windows 10'
            elif 'Windows 11' in os_name: os_group = 'Windows 11'
            elif 'Server' in os_name: os_group = 'Windows Server'
            elif 'Linux' in os_name: os_group = 'Linux'
            else: os_group = 'Outros'
            
            by_os[os_group] = by_os.get(os_group, 0) + 1
            if a.get('status_code') == 'ONLINE': online_count += 1
            
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        report_id = f"report_inv_{int(time.time())}"
        
        html = f"""
        <div id="{report_id}" style="background:white; color:black; padding:20px; border-radius:8px; font-family:sans-serif;">
            <div style="border-bottom:2px solid #ddd; padding-bottom:10px; margin-bottom:15px; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="margin:0; font-size:18px;">Relatório Geral de Inventário</h2>
                <span style="font-size:12px; color:#666;">Gerado em: {now_str}</span>
            </div>
            
            <div style="display:flex; gap:20px; margin-bottom:20px; padding:15px; background:#f9fafb; border-radius:6px; border:1px solid #eee;">
                <div>
                    <div style="font-size:10px; color:#666; text-transform:uppercase;">Total Ativos</div>
                    <div style="font-size:24px; font-weight:bold;">{total_assets}</div>
                </div>
                <div style="border-left:1px solid #ddd; padding-left:20px;">
                    <div style="font-size:10px; color:#666; text-transform:uppercase;">Online Agora</div>
                    <div style="font-size:24px; font-weight:bold; color:#10b981;">{online_count}</div>
                </div>
            </div>
            
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <tr style="background:#f3f4f6; text-align:left;">
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Sistema Operacional (Grupo)</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">Quantidade</th>
                    <th style="padding:8px; border-bottom:1px solid #ddd;">% do Parque</th>
                </tr>
        """
        
        sorted_os = sorted(by_os.items(), key=lambda x: x[1], reverse=True)
        for os_name, count in sorted_os:
            pct = round((count / total_assets) * 100, 1)
            html += f"""
                <tr>
                    <td style="padding:8px; border-bottom:1px solid #eee; font-weight:bold;">{os_name}</td>
                    <td style="padding:8px; border-bottom:1px solid #eee;">{count}</td>
                    <td style="padding:8px; border-bottom:1px solid #eee;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div style="flex:1; height:6px; background:#eee; border-radius:3px; overflow:hidden;">
                                <div style="width:{pct}%; height:100%; background:#2563eb;"></div>
                            </div>
                            <span>{pct}%</span>
                        </div>
                    </td>
                </tr>
            """
        
        html += f"""
            </table>
        </div>
        """
        return jsonify({'description': f'Inventário resumido gerado com sucesso:<br><br>{html}'})
    
    return jsonify({'description': 'Tipo de relatório não suportado.'})
