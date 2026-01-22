@echo off
setlocal EnableDelayedExpansion

:: NetAudit Enterprise - Instalador Profissional
echo ============================================
echo    NetAudit Enterprise - Instalador
echo ============================================
echo.

:: Verificar se é Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERRO: Este instalador precisa de permissoes de Administrador.
    echo.
    echo Clique com botao direito neste arquivo e selecione "Executar como administrador"
    echo.
    pause
    exit /b 1
)

:: Diretório de instalação
set "INSTALL_DIR=C:\Program Files\NetAudit Enterprise"
set "APPDATA_DIR=%APPDATA%\NetAudit Enterprise"

echo [1/4] Verificando instalacao anterior...
if exist "%INSTALL_DIR%\NetAudit_System.exe" (
    echo NetAudit ja esta instalado em:
    echo %INSTALL_DIR%
    echo.
    choice /C YN /M "Deseja reinstalar"
    if errorlevel 2 (
        echo Instalacao cancelada.
        pause
        exit /b 0
    )
)

echo.
echo [2/4] Criando diretorios...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%APPDATA_DIR%" mkdir "%APPDATA_DIR%"

echo.
echo [3/4] Baixando NetAudit do GitHub... (Aguarde, pode demorar)
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/funesa/NetAudit/raw/master/dist/NetAudit_Portable.zip' -OutFile '%TEMP%\NetAudit.zip'"

if not exist "%TEMP%\NetAudit.zip" (
    echo ERRO: Falha ao baixar o NetAudit.
    echo Verifique sua conexao com a internet.
    pause
    exit /b 1
)

echo.
echo [4/4] Instalando arquivos...
powershell -Command "Expand-Archive -Path '%TEMP%\NetAudit.zip' -DestinationPath '%TEMP%\NetAuditTemp' -Force"

:: Mover para o local correto
xcopy "%TEMP%\NetAuditTemp\NetAudit_System" "%INSTALL_DIR%\NetAudit_System\" /E /I /H /Y >nul 2>&1

:: Limpar temp
rmdir /S /Q "%TEMP%\NetAuditTemp" >nul 2>&1
del "%TEMP%\NetAudit.zip" >nul 2>&1

:: Verificar se instalou corretamente
if not exist "%INSTALL_DIR%\NetAudit_System\NetAudit_System.exe" (
    echo.
    echo ERRO: Falha na instalacao dos arquivos.
    echo O executável nao foi encontrado em:
    echo %INSTALL_DIR%\NetAudit_System\NetAudit_System.exe
    pause
    exit /b 1
)

:: Criar atalho no Menu Iniciar
echo Criando atalho no Menu Iniciar...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%ProgramData%\Microsoft\Windows\Start Menu\Programs\NetAudit Enterprise.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\NetAudit_System\NetAudit_System.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\NetAudit_System'; $Shortcut.Save()"

:: Criar atalho na Área de Trabalho
echo Criando atalho na Area de Trabalho...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%PUBLIC%\Desktop\NetAudit Enterprise.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\NetAudit_System\NetAudit_System.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\NetAudit_System'; $Shortcut.Save()"

echo.
echo ============================================
echo    Instalacao Concluida com Sucesso!
echo ============================================
echo.
echo Local: %INSTALL_DIR%
echo.
echo Atalhos criados em:
echo  - Menu Iniciar
echo  - Area de Trabalho
echo.
choice /C YN /M "Deseja iniciar o NetAudit agora"
if errorlevel 2 goto :END

start "" "%INSTALL_DIR%\NetAudit_System\NetAudit_System.exe"

:END
echo.
echo Instalacao finalizada!
pause
