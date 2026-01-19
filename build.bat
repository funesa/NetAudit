@echo off
echo Building NetAudit Enterprise...
pyinstaller --noconfirm --log-level=WARN --onefile --windowed --icon "netaudit.ico" --add-data "templates;templates" --add-data "static;static" --add-data "scripts;scripts" --add-data "c:/Users/POFJunior/AppData/Local/Programs/Python/Python312/Lib/site-packages/customtkinter;customtkinter/" --hidden-import "waitress" --hidden-import "pystray" --hidden-import "PIL" --hidden-import "customtkinter" --hidden-import "cryptography" --name "NetAudit_Server_Secure" launcher.py
echo.
echo Build Complete!
echo You can find the executable at: dist\NetAudit_Enterprise.exe
echo.
pause
