@echo off
REM ============================================
REM NetAudit - Backend Production Build
REM ============================================
echo.
echo [1/2] Limpando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo.
echo [2/2] Compilando backend com PyInstaller...
pyinstaller build.spec --clean

echo.
echo Build concluido!
echo Executavel gerado em: dist\NetAudit.exe
echo.
pause
