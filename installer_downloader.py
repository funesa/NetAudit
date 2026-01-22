"""
Instalador inteligente do NetAudit - Baixa e instala do GitHub
Este é um instalador LEVE que não embute o aplicativo.
"""
import os
import sys
import zipfile
import tempfile
import subprocess
import requests
from pathlib import Path
from tkinter import Tk, messagebox

def show_message(title, message, error=False):
    """Mostra mensagem para o usuário"""
    root = Tk()
    root.withdraw()
    if error:
        messagebox.showerror(title, message)
    else:
        messagebox.showinfo(title, message)
    root.destroy()

def install_netaudit():
    """Baixa e instala o NetAudit"""
    try:
        # Diretório de instalação
        appdata = Path(os.environ.get('APPDATA'))
        install_dir = appdata / 'NetAudit_System'
        exe_path = install_dir / 'NetAudit_System.exe'
        
        # Se já existe, apenas executa
        if exe_path.exists():
            print("NetAudit já instalado. Iniciando...")
            subprocess.Popen([str(exe_path)], cwd=str(install_dir), 
                           creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            return
        
        print("Baixando NetAudit do GitHub...")
        show_message("Instalação", "Baixando NetAudit Enterprise...\nIsso pode levar alguns minutos.", error=False)
        
        # URL do ZIP no GitHub
        zip_url = "https://github.com/funesa/NetAudit/raw/master/dist/NetAudit_Portable.zip"
        
        # Baixar
        response = requests.get(zip_url, stream=True, timeout=300)
        response.raise_for_status()
        
        # Salvar temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name
        
        print("Extraindo arquivos...")
        
        # Extrair
        with zipfile.ZipFile(tmp_path, 'r') as zf:
            zf.extractall(appdata)
        
        # Limpar temp
        os.unlink(tmp_path)
        
        print("Instalação concluída!")
        show_message("Sucesso", "NetAudit Enterprise instalado com sucesso!\n\nIniciando aplicação...", error=False)
        
        # Executar
        subprocess.Popen([str(exe_path)], cwd=str(install_dir),
                       creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        
    except Exception as e:
        show_message("Erro de Instalação", f"Falha ao instalar NetAudit:\n\n{str(e)}\n\nVerifique sua conexão com a internet.", error=True)
        sys.exit(1)

if __name__ == '__main__':
    install_netaudit()
