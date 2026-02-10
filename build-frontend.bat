@echo off
REM ============================================
REM NetAudit - Frontend Production Build
REM ============================================
echo.
echo [1/3] Instalando dependencias...
cd frontend
call npm install

echo.
echo [2/3] Compilando frontend para producao...
call npm run build

echo.
echo [3/3] Build concluido!
echo Arquivos gerados em: frontend\dist\
echo.
pause
