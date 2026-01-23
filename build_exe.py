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

print(f"Iniciando compilacao do {APP_NAME} (MODO ONEFILE ROBUSTO)...")

PYTHON_DIR = "C:\\Users\\POFJunior\\AppData\\Local\\Programs\\Python\\Python312"

# 3. Argumentos do PyInstaller
args = [
    MAIN_SCRIPT,
    f'--name={APP_NAME}',
    '--onefile',                   # MODO ARQUIVO ÚNICO (Conforme solicitado)
    '--noconsole',                 
    '--clean',
    '--noupx',                     # Desabilita UPX (evita problemas de DLL)
    
    # Incluir Pastas Importantes
    '--add-data=templates;templates',
    '--add-data=static;static',
    '--add-data=scripts;scripts',
    
    # ---------------------------------------------------------
    # FIX DEFINITIVO DE DLL: Incluir Runtimes do Visual C++
    # ---------------------------------------------------------
    # Python DLL
    # FIX ULTIMATE DE DLL: Incluir TUDO que o Python precisa
    # ---------------------------------------------------------
    # 1. Python Engine
    f'--add-binary={PYTHON_DIR}\\python312.dll;.',
    
    # 2. Visual C++ Runtime (Core)
    f'--add-binary={PYTHON_DIR}\\vcruntime140.dll;.',
    f'--add-binary={PYTHON_DIR}\\vcruntime140_1.dll;.',
    
    # 3. Standard C++ Library & Concurrency
    f'--add-binary=C:\\Windows\\System32\\msvcp140.dll;.',
    f'--add-binary=C:\\Windows\\System32\\msvcp140_1.dll;.',
    f'--add-binary=C:\\Windows\\System32\\concrt140.dll;.',
    
    # 4. Universal C Runtime (UCRT) - Critical for modern Windows
    f'--add-binary=C:\\Windows\\System32\\ucrtbase.dll;.',
    
    # 5. SQLite
    f'--add-binary={PYTHON_DIR}\\DLLs\\sqlite3.dll;.',
    
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
    '--hidden-import=sqlalchemy',
    '--hidden-import=sqlalchemy.ext.declarative',
    '--hidden-import=sqlalchemy.orm',
    '--hidden-import=alembic',
    '--hidden-import=pkg_resources', # Frequentemente necessário para metadados
    '--hidden-import=apscheduler',
    '--hidden-import=apscheduler.triggers.interval',
    '--hidden-import=apscheduler.schedulers.background',
    '--hidden-import=tzlocal',
    
    # Coletar todos os dados e metadados dos subpacotes críticos
    '--collect-all=customtkinter',
    '--collect-all=flask',
    '--collect-all=ldap3',
    '--collect-all=sqlalchemy',
    '--collect-all=alembic',
    '--collect-all=engineio',
    '--collect-all=socketio',
    '--collect-all=apscheduler',
    '--collect-all=tzlocal',
    
    # Excluir módulos desnecessários para reduzir tamanho e conflitos
    # '--exclude-module=tkinter.test', # Comentado para garantir que o tkinter funcione
    '--exclude-module=matplotlib',
    '--exclude-module=scipy',
    '--exclude-module=pytest',
]

# Adicionar ícone se existir
if os.path.exists(ICON_PATH):
    args.append(f'--icon={ICON_PATH}')

# 4. Rodar o PyInstaller
PyInstaller.__main__.run(args)

print(f"\n✅ Sucesso! O executável está em 'dist/'.")
print(f"👉 dist/{APP_NAME}.exe")
