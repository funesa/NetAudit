import os
import sys
import subprocess
import requests
import hashlib

# ============================================
# 🔧 CONFIGURAÇÃO DE ATUALIZAÇÃO REMOTA
# ============================================
# INSTRUÇÕES:
# 1. Hospede o arquivo version.json na internet (GitHub, Google Drive, seu servidor)
# 2. O version.json deve conter: latest_version, download_url, sha256
# 3. Recompile o executável: pyinstaller build.spec
#
# EXEMPLO version.json:
# {
#   "latest_version": "2.0.0",
#   "download_url": "https://github.com/funesa/NetAudit/releases/download/v2.0.0/NetAudit.exe",
#   "sha256": "abc123...",
#   "release_notes": "Correções de estabilidade"
# }
# ============================================

UPDATE_URL = "https://raw.githubusercontent.com/funesa/NetAudit/master/version.json"

def check_for_updates(current_version):
    """
    Verifica se existe uma nova versão disponível.
    
    Args:
        current_version: Versão atual do sistema (ex: "1.0.0")
        
    Returns:
        tuple: (has_update, latest_version, download_url, sha256)
    """
    try:
        response = requests.get(UPDATE_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            latest = data.get("latest_version")
            download_url = data.get("download_url")
            sha256 = data.get("sha256", "")
            
            # Comparação simples de versão (string)
            if latest and latest > current_version:
                return True, latest, download_url, sha256
    except Exception as e:
        print(f"[UPDATE] Erro ao verificar atualização: {e}")
    
    return False, None, None, None

def verify_file_hash(filepath, expected_hash):
    """
    Verifica a integridade do arquivo baixado usando SHA256.
    
    Args:
        filepath: Caminho do arquivo a verificar
        expected_hash: Hash SHA256 esperado
        
    Returns:
        bool: True se o hash corresponde, False caso contrário
    """
    if not expected_hash:
        print("[UPDATE] AVISO: Nenhum hash fornecido, pulando validação")
        return True
    
    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            # Ler em chunks para não sobrecarregar memória
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        calculated_hash = sha256_hash.hexdigest()
        
        if calculated_hash.lower() == expected_hash.lower():
            print(f"[UPDATE] ✓ Hash validado: {calculated_hash[:16]}...")
            return True
        else:
            print(f"[UPDATE] ✗ Hash inválido!")
            print(f"  Esperado: {expected_hash[:16]}...")
            print(f"  Obtido:   {calculated_hash[:16]}...")
            return False
    except Exception as e:
        print(f"[UPDATE] Erro ao verificar hash: {e}")
        return False

def run_update(download_url, latest_version, expected_sha256=""):
    """
    Baixa a atualização e executa o script de substituição.
    
    Args:
        download_url: URL do novo executável
        latest_version: Versão que será instalada
        expected_sha256: Hash SHA256 esperado do arquivo
        
    Returns:
        bool: True se o update foi iniciado com sucesso
    """
    try:
        # 1. Verificar se está rodando como executável
        if not getattr(sys, 'frozen', False):
            print("[UPDATE] Modo desenvolvimento detectado, update desabilitado")
            return False
        
        current_exe = sys.executable
        temp_exe = current_exe.replace(".exe", "_new.exe")
        
        # 2. Download do novo executável
        print(f"[UPDATE] Baixando de {download_url}...")
        response = requests.get(download_url, stream=True, timeout=120)
        
        if response.status_code != 200:
            print(f"[UPDATE] Erro HTTP {response.status_code}")
            return False
        
        # Baixar com validação de cabeçalho
        with open(temp_exe, "wb") as f:
            first_chunk = True
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    if first_chunk:
                        # Verificar cabeçalho MZ (executável Windows)
                        if not chunk.startswith(b'MZ'):
                            print("[UPDATE] Arquivo baixado não é um executável válido")
                            f.close()
                            if os.path.exists(temp_exe):
                                os.remove(temp_exe)
                            return False
                        first_chunk = False
                    f.write(chunk)
        
        print(f"[UPDATE] Download concluído: {os.path.getsize(temp_exe)} bytes")
        
        # 3. Validar hash SHA256
        if not verify_file_hash(temp_exe, expected_sha256):
            print("[UPDATE] Validação de integridade falhou, abortando")
            if os.path.exists(temp_exe):
                os.remove(temp_exe)
            return False
        
        # 4. Criar script BAT otimizado com timeout de 3s
        exe_name = os.path.basename(current_exe)
        temp_name = os.path.basename(temp_exe)
        
        bat_content = f"""@echo off
title Atualizando NetAudit para v{latest_version}
echo Aguardando finalizacao do processo...
timeout /t 3 /nobreak > NUL

taskkill /F /IM "{exe_name}" > NUL 2>&1
timeout /t 1 /nobreak > NUL

del /F /Q "{exe_name}"
if exist "{exe_name}" (
    timeout /t 2 /nobreak > NUL
    del /F /Q "{exe_name}"
)

move "{temp_name}" "{exe_name}"
if errorlevel 1 (
    echo ERRO: Falha ao instalar atualizacao
    pause
    exit
)

echo Atualizacao concluida! Iniciando v{latest_version}...
start "" "{exe_name}"
del "%~f0"
"""
        
        bat_path = "update_installer.bat"
        with open(bat_path, "w", encoding="utf-8") as bat:
            bat.write(bat_content)
        
        print(f"[UPDATE] Script de instalação criado: {bat_path}")
        
        # 5. Executar BAT e terminar IMEDIATAMENTE
        subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        print("[UPDATE] Processo de atualização iniciado, encerrando aplicação...")
        
        # CRÍTICO: Usar os._exit() para garantir término imediato
        # Não usar sys.exit() pois pode ser capturado por exception handlers
        os._exit(0)
        
    except Exception as e:
        print(f"[UPDATE] Erro durante atualização: {e}")
        return False
