import PyInstaller.__main__
import os
import shutil
import sys

# 1. Configurações
APP_NAME = "NetAudit_System"
MAIN_SCRIPT = "launcher.py"
ICON_PATH = "static/netaudit.ico"

# 2. Limpar builds anteriores
if os.path.exists("build"):
    shutil.rmtree("build")
if os.path.exists("dist"):
    shutil.rmtree("dist")

print(f"🔨 Iniciando compilacao do {APP_NAME} (Modo Robusto - Onedir)...")

# 3. Localizar python312.dll
python_dll = os.path.join(sys.base_prefix, "python312.dll")
if not os.path.exists(python_dll):
    print(f"⚠️  AVISO: python312.dll não encontrado em {python_dll}")
    python_dll = None

# 4. Argumentos do PyInstaller (ONEDIR para evitar problemas de DLL)
args = [
    MAIN_SCRIPT,
    f'--name={APP_NAME}',
    '--onedir',                    # <-- MUDANÇA: Gera pasta com exe + DLLs (mais estável)
    '--noconsole',                 
    '--clean',
    
    # Incluir Pastas Importantes
    '--add-data=templates;templates',
    '--add-data=static;static',
    '--add-data=scripts;scripts',
    
    # Incluir python312.dll explicitamente
    f'--add-binary={python_dll};.' if python_dll else '',
    
    # Imports Ocultos Expandidos
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
    
    # Coletar todos os subpacotes
    '--collect-all=customtkinter',
    '--collect-all=flask',
    '--collect-all=ldap3',
    
    # Excluir módulos desnecessários
    '--exclude-module=tkinter.test',
    '--exclude-module=matplotlib',
    '--exclude-module=scipy',
]

# Remover strings vazias
args = [a for a in args if a]

# Adicionar ícone se existir
if os.path.exists(ICON_PATH):
    args.append(f'--icon={ICON_PATH}')

# 5. Rodar o PyInstaller
PyInstaller.__main__.run(args)

# 6. Criar um launcher.bat para facilitar execução
dist_folder = os.path.join("dist", APP_NAME)
if os.path.exists(dist_folder):
    launcher_bat = os.path.join("dist", f"Iniciar_{APP_NAME}.bat")
    with open(launcher_bat, "w") as f:
        f.write(f"""@echo off
cd /d "%~dp0"
start "" "{APP_NAME}\\{APP_NAME}.exe"
""")
    print(f"\n✅ Sucesso! O executável está na pasta 'dist/{APP_NAME}/'.")
    print(f"👉 Execute: dist/Iniciar_{APP_NAME}.bat")
    print(f"👉 Ou diretamente: dist/{APP_NAME}/{APP_NAME}.exe")
else:
    print(f"\n✅ Compilação concluída!")
