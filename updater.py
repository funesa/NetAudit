import os
import sys
import time
import subprocess
import requests
import tkinter as tk
from tkinter import messagebox

# ============================================
# 🔧 CONFIGURAÇÃO DE ATUALIZAÇÃO REMOTA
# ============================================
# INSTRUÇÕES:
# 1. Hospede o arquivo version.json na internet (GitHub, Google Drive, seu servidor)
# 2. Cole o link completo abaixo
# 3. Recompile o executável: python build_exe.py
#
# EXEMPLO GitHub:
# UPDATE_URL = "https://raw.githubusercontent.com/SEU_USUARIO/netaudit/main/version.json"
#
# EXEMPLO Google Drive (pegue o ID do arquivo compartilhado):
# UPDATE_URL = "https://drive.google.com/uc?export=download&id=SEU_ID_AQUI"
#
# EXEMPLO Servidor Próprio:
# UPDATE_URL = "https://seusite.com.br/netaudit/version.json"
# ============================================

UPDATE_URL = "https://raw.githubusercontent.com/funesa/NetAudit/master/version.json"  # ✅ CORRIGIDO PARA MASTER!

def check_for_updates(current_version):
    """Verifica se existe uma nova versão disponível."""
    try:
        response = requests.get(UPDATE_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            latest = data.get("latest_version")
            download_url = data.get("download_url")
            
            # Comparação simples de versão
            if latest and latest > current_version:
                return True, latest, download_url
    except Exception as e:
        print(f"Erro ao verificar update: {e}")
    return False, None, None

def run_update(download_url, latest_version):
    """Baixa a atualização EXE e executa o script de troca."""
    try:
        import ctypes
        
        # Verificar se está rodando como admin
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        
        # Se não for admin, relançar como admin
        if not is_admin:
            import sys
            if getattr(sys, 'frozen', False):
                # Se for executável, relançar com elevação
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, 
                    "--update " + download_url + " " + latest_version, 
                    None, 1
                )
                sys.exit(0)
        
        # 1. Definir caminhos
        current_exe = sys.executable
        if not getattr(sys, 'frozen', False):
            # Para testes em modo dev (.py), não faz nada
            return False

        temp_exe = current_exe.replace(".exe", "_new.exe")
        
        # 2. Download
        print(f"Baixando atualização de {download_url}...")
        response = requests.get(download_url, stream=True, timeout=60)
        if response.status_code != 200:
            messagebox.showerror("Erro", f"Servidor de download retornou erro {response.status_code}")
            return False

        with open(temp_exe, "wb") as f:
            first_chunk = True
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    if first_chunk:
                        # Verifica o cabeçalho 'MZ' de executáveis Windows
                        if not chunk.startswith(b'MZ'):
                            messagebox.showerror("Erro", "O download parece corrompido ou inválido (Formato EXE incorreto).")
                            f.close()
                            os.remove(temp_exe)
                            return False
                    first_chunk = False
                    f.write(chunk)
        
        # 3. Criar BAT de substituição robusto com Retry
        exe_name = os.path.basename(current_exe)
        temp_name = os.path.basename(temp_exe)
        
        bat_content = f"""
@echo off
title Atualizando NetAudit...
echo Aguardando finalizacao do processo...
timeout /t 3 /nobreak > NUL

:RETRY_DEL
echo Tentando deletar versao antiga...
del /f /q "{exe_name}"
if exist "{exe_name}" (
    echo Arquivo ainda bloqueado. Tentando novamente em 2 segundos...
    timeout /t 2 /nobreak > NUL
    goto RETRY_DEL
)

echo Instalando nova versao...
rename "{temp_name}" "{exe_name}"
if errorlevel 1 (
    echo Erro ao renomear arquivo novo.
    pause
    exit
)

echo Atualizacao concluida para a versão {latest_version}!
start "" "{exe_name}"
del "%~f0"
"""
        with open("updater.bat", "w") as bat:
            bat.write(bat_content)
            
        # 4. Executar BAT e sair
        subprocess.Popen("updater.bat", shell=True)
        return True
    except Exception as e:
        messagebox.showerror("Erro de Atualização", f"Falha ao baixar/instalar: {e}")
        return False
