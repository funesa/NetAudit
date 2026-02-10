@echo off
REM ============================================
REM NetAudit - Complete Build Script
REM ============================================
REM Este script compila frontend, backend e gera o instalador
REM ============================================

echo.
echo ============================================
echo NetAudit - Build Completo
echo ============================================
echo.

REM Passo 1: Build Frontend
echo [1/5] Compilando Frontend React...
cd frontend
call npm install
call npm run build
if errorlevel 1 (
    echo ERRO: Build do frontend falhou!
    pause
    exit /b 1
)
cd ..
echo Frontend OK!
echo.

REM Passo 2: Limpar builds anteriores
echo [2/5] Limpando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist installer\Output rmdir /s /q installer\Output
echo Limpeza OK!
echo.

REM Passo 3: Build Backend
echo [3/5] Compilando Backend com PyInstaller...
pyinstaller build.spec --clean
if errorlevel 1 (
    echo ERRO: Build do backend falhou!
    pause
    exit /b 1
)
echo Backend OK!
echo.

REM Passo 4: Copiar Frontend para Dist
echo [4/5] Integrando Frontend no executavel...
xcopy /E /I /Y frontend\dist dist\frontend
echo Integracao OK!
echo.

REM Passo 5: Gerar Instalador com Inno Setup
echo [5/5] Gerando instalador com Inno Setup...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" NetAudit-Installer.iss
if errorlevel 1 (
    echo ERRO: Inno Setup nao encontrado ou falhou!
    echo Instale o Inno Setup 6 de: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)
echo Instalador OK!
echo.

REM Passo 6: Calcular SHA256
echo ============================================
echo Build Concluido com Sucesso!
echo ============================================
echo.
echo Instalador gerado em: installer\Output\NetAudit-Setup.exe
echo.
echo Calculando SHA256...
powershell -Command "Get-FileHash installer\Output\NetAudit-Setup.exe -Algorithm SHA256 | Select-Object -ExpandProperty Hash"
echo.
echo IMPORTANTE: Atualize o SHA256 em update-server\version.json
echo.
pause
