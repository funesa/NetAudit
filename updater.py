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
    """Baixa a atualização (EXE ou ZIP) e executa o script de troca."""
    try:
        # 1. Definir caminhos
        current_exe = sys.executable
        if not getattr(sys, 'frozen', False):
            # Para testes em modo dev (.py), não faz nada
            return False

        is_zip = download_url.lower().endswith(".zip")
        temp_file = "update.zip" if is_zip else current_exe.replace(".exe", "_new.exe")
        
        # 2. Download
        print(f"Baixando atualização de {download_url}...")
        response = requests.get(download_url, stream=True, timeout=60)
        if response.status_code != 200:
            messagebox.showerror("Erro", f"Servidor de download retornou erro {response.status_code}")
            return False

        with open(temp_file, "wb") as f:
            first_chunk = True
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    if first_chunk and not is_zip:
                        # Verifica o cabeçalho 'MZ' apenas para executáveis diretos
                        if not chunk.startswith(b'MZ'):
                            messagebox.showerror("Erro", "O download parece corrompido ou inválido (Not a PE file).")
                            f.close()
                            os.remove(temp_file)
                            return False
                    first_chunk = False
                    f.write(chunk)
        
        # 3. Criar BAT de substituição robusto
        exe_name = os.path.basename(current_exe)
        
        if is_zip:
            # Script para extrair ZIP e substituir arquivos (PowerShell)
            bat_content = f"""
@echo off
title Atualizando NetAudit...
echo Aguardando finalizacao do processo...
timeout /t 3 /nobreak > NUL
echo Extraindo arquivos novos...
powershell -Command "Expand-Archive -Path 'update.zip' -DestinationPath 'temp_update' -Force"
if errorlevel 1 (
    echo Erro ao extrair arquivos.
    pause
    exit
)
echo Substituindo arquivos...
xcopy /y /s /e "temp_update\\NetAudit_System\\*" "."
rd /s /q "temp_update"
del /f /q "update.zip"
echo Atualizacao concluida para a versão {latest_version}!
start "" "{exe_name}"
del "%~f0"
"""
        else:
            # Script clássico para EXE único
            temp_name = os.path.basename(temp_file)
            bat_content = f"""
@echo off
title Atualizando NetAudit...
echo Aguardando finalizacao do processo...
timeout /t 3 /nobreak > NUL
del /f /q "{exe_name}"
rename "{temp_name}" "{exe_name}"
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
