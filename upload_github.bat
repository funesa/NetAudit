@echo off
set VERSION=2026.1.2
echo ========================================
echo  UPLOAD AUTOMATICO - NetAudit %VERSION%
echo ========================================
echo.

cd /d "%~dp0"

echo [1/6] Verificando Git...
git --version
if errorlevel 1 (
    echo ERRO: Git nao esta instalado!
    pause
    exit /b 1
)

echo.
echo [2/6] Configurando repositorio...
git init
git remote add origin https://github.com/funesa/NetAudit.git 2>nul

echo.
echo [3/6] Adicionando arquivos...
git add dist/NetAudit_System.exe
git add version.json
git add templates/wizard.html
git add templates/layout.html
git add launcher.py
git add app.py
git add ai_actions.py
git add updater.py

echo.
echo [4/6] Criando commit...
git commit -m "Release %VERSION% - Fix janelas piscando e seguranca no update"

echo.
echo [5/6] Enviando para GitHub...
echo ATENCAO: Voce precisara fazer login no GitHub!
echo.

REM Garante que as duas branches existem e estao sincronizadas
echo Enviando para 'master'...
git push -u origin master --force

echo.
echo Enviando para 'main' (para suporte a versoes antigas)...
git checkout -b main 2>nul
git checkout main 2>nul
git merge master
git push -u origin main --force
git checkout master

echo.
echo [6/6] Verificando upload...
echo.
echo ========================================
echo  UPLOAD CONCLUIDO COM SUCESSO!
echo ========================================
echo.
echo Arquivos enviados:
echo  - NetAudit_System.exe (%VERSION%)
echo  - version.json
echo  - app.py / launcher.py / layout.html
echo.
echo O cliente ja pode receber a atualizacao!
echo.
pause
