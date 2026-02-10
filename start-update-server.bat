@echo off
REM ============================================
REM NetAudit Update Server - Iniciar
REM ============================================
echo.
echo Iniciando NetAudit Update Server...
echo Servidor: http://172.23.51.50:8080
echo.
echo Pressione CTRL+C para parar
echo.

cd update-server
python server.py
