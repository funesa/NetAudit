import PyInstaller.__main__
import os
import shutil

# 1. Configurações
APP_NAME = "NetAudit_System"
MAIN_SCRIPT = "launcher.py"
ICON_PATH = "static/netaudit.ico"

# 2. Limpar builds anteriores
if os.path.exists("build"):
    shutil.rmtree("build")
if os.path.exists("dist"):
    shutil.rmtree("dist")

print(f"🔨 Iniciando compilacao do {APP_NAME} (Arquivo Único Otimizado)...")

# 3. Argumentos do PyInstaller
args = [
    MAIN_SCRIPT,
    f'--name={APP_NAME}',
    '--onefile',                   # Arquivo único
    '--noconsole',                 
    '--clean',
    '--noupx',                     # Desabilita UPX (evita problemas de DLL)
    
    # Incluir Pastas Importantes
    '--add-data=templates;templates',
    '--add-data=static;static',
    '--add-data=scripts;scripts',
    
    # Imports Ocultos Essenciais
    '--hidden-import=engineio.async_drivers.threading',
    '--hidden-import=socketio',
    '--hidden-import=flask_socketio',
    '--hidden-import=PIL',
    '--hidden-import=PIL._tkinter_finder',
    '--hidden-import=pystray',
    '--hidden-import=customtkinter',
    '--hidden-import=ldap3',
    '--hidden-import=pysnmp',
    '--hidden-import=requests',
    '--hidden-import=flask',
    '--hidden-import=flask_session',
    '--hidden-import=werkzeug',
    '--hidden-import=jinja2',
    '--hidden-import=dotenv',
    '--hidden-import=psutil',
    '--hidden-import=win32com.client',
    '--hidden-import=win32api',
    '--hidden-import=win32con',
    
    # Coletar todos os subpacotes críticos
    '--collect-all=customtkinter',
    '--collect-all=flask',
    '--collect-all=ldap3',
    
    # Excluir módulos desnecessários
    '--exclude-module=tkinter.test',
    '--exclude-module=matplotlib',
    '--exclude-module=scipy',
    '--exclude-module=pytest',
    '--exclude-module=sqlalchemy',
    '--exclude-module=alembic',
]

# Adicionar ícone se existir
if os.path.exists(ICON_PATH):
    args.append(f'--icon={ICON_PATH}')

# 4. Rodar o PyInstaller
PyInstaller.__main__.run(args)

print(f"\n✅ Sucesso! O executável está em 'dist/'.")
print(f"👉 dist/{APP_NAME}.exe")
