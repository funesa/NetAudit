"""
Cria um instalador auto-extraível (EXE único) a partir do build onedir.
Este script empacota a pasta dist/NetAudit_System em um único executável.
"""
import os
import shutil
import base64
import zipfile
from pathlib import Path

print("🔨 Criando instalador auto-extraível...")

# 1. Compactar a pasta dist/NetAudit_System
dist_folder = Path("dist/NetAudit_System")
zip_path = Path("dist/NetAudit_Portable.zip")

if zip_path.exists():
    zip_path.unlink()

print(f"📦 Compactando {dist_folder}...")
shutil.make_archive(str(zip_path.with_suffix('')), 'zip', dist_folder.parent, dist_folder.name)

# 2. Criar o script do wrapper
wrapper_code = '''
import os
import sys
import zipfile
import tempfile
import subprocess
from pathlib import Path

def extract_and_run():
    """Extrai o aplicativo e executa"""
    # Diretório de instalação permanente
    install_dir = Path(os.environ.get('APPDATA')) / 'NetAudit Enterprise'
    install_dir.mkdir(parents=True, exist_ok=True)
    
    exe_path = install_dir / 'NetAudit_System.exe'
    
    # Se já existe e está atualizado, apenas executa
    if exe_path.exists():
        print("Iniciando NetAudit...")
        subprocess.Popen([str(exe_path)], cwd=str(install_dir))
        return
    
    print("Instalando NetAudit Enterprise...")
    
    # Extrair ZIP embutido
    zip_data = base64.b64decode(EMBEDDED_ZIP)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        tmp.write(zip_data)
        tmp_path = tmp.name
    
    try:
        with zipfile.ZipFile(tmp_path, 'r') as zf:
            zf.extractall(install_dir.parent)
        
        print("Instalação concluída!")
        subprocess.Popen([str(exe_path)], cwd=str(install_dir))
        
    finally:
        os.unlink(tmp_path)

if __name__ == '__main__':
    extract_and_run()
'''

# 3. Ler o ZIP e converter para base64
print("📝 Embutindo dados no wrapper...")
with open(zip_path, 'rb') as f:
    zip_bytes = f.read()
    zip_b64 = base64.b64encode(zip_bytes).decode('ascii')

# 4. Inserir o ZIP no código
wrapper_code = wrapper_code.replace('EMBEDDED_ZIP', f'"{zip_b64}"')

# 5. Salvar o wrapper
wrapper_path = Path("installer_wrapper.py")
with open(wrapper_path, 'w', encoding='utf-8') as f:
    f.write(wrapper_code)

print(f"✅ Wrapper criado: {wrapper_path}")
print(f"📦 Tamanho do ZIP: {len(zip_bytes) / 1024 / 1024:.2f} MB")

# 6. Compilar o wrapper com PyInstaller
print("🔨 Compilando instalador final...")
import PyInstaller.__main__

args = [
    str(wrapper_path),
    '--name=NetAudit_Installer',
    '--onefile',
    '--noconsole',
    '--clean'
]

if Path('static/netaudit.ico').exists():
    args.append('--icon=static/netaudit.ico')

PyInstaller.__main__.run(args)

print("\n✅ SUCESSO!")
print("👉 Arquivo final: dist/NetAudit_Installer.exe")
print("   Este é um EXE único que instala e executa o NetAudit.")
