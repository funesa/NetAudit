@echo off
set VERSION=2026.1.3
echo ========================================
echo  UPLOAD RELEASE - NetAudit %VERSION%
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] Verificando Git...
git --version
if errorlevel 1 (
    echo ERRO: Git nao esta instalado!
    pause
    exit /b 1
)

echo.
echo [2/5] Configurando repositorio...
git init
git remote add origin https://github.com/funesa/NetAudit.git 2>nul

echo.
echo [3/5] Criando tag de release...
git tag -d v%VERSION% 2>nul
git tag v%VERSION%

echo.
echo [4/5] Adicionando arquivos...
git add version.json
git add launcher.py
git add app.py
git add build_exe.py
git add ai_actions.py
git add updater.py

echo.
echo [5/5] Criando commit e enviando...
git commit -m "Release %VERSION% - Empacotamento robusto onedir + Fix DLL + Fix janelas"

echo.
echo Enviando para 'master'...
git push -u origin master --force

echo.
echo Enviando tag...
git push origin v%VERSION% --force

echo.
echo ========================================
echo  AGORA CRIE O RELEASE NO GITHUB:
echo ========================================
echo.
echo 1. Acesse: https://github.com/funesa/NetAudit/releases/new
echo 2. Tag: v%VERSION%
echo 3. Titulo: NetAudit v%VERSION% - Versao Estavel
echo 4. Descricao: Correcao definitiva de DLLs e janelas piscando
echo 5. Anexe o arquivo: dist\NetAudit_System_v%VERSION%.zip
echo 6. Publique o release
echo.
pause
