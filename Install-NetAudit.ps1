# NetAudit Enterprise - Instalador PowerShell Puro
# Este script NÃO depende de PyInstaller, evitando TODOS os conflitos

Write-Host "=== NetAudit Enterprise - Instalador ===" -ForegroundColor Cyan
Write-Host ""

# Diretório de instalação
$InstallDir = "$env:APPDATA\NetAudit_System"
$ExePath = "$InstallDir\NetAudit_System.exe"

# Se já existe, apenas executa
if (Test-Path $ExePath) {
    Write-Host "NetAudit já instalado. Iniciando..." -ForegroundColor Green
    Start-Process $ExePath -WorkingDirectory $InstallDir
    exit 0
}

# Baixar
Write-Host "Baixando NetAudit do GitHub..." -ForegroundColor Yellow
$ZipUrl = "https://github.com/funesa/NetAudit/raw/master/dist/NetAudit_Portable.zip"
$TempZip = "$env:TEMP\NetAudit_Temp.zip"

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $ZipUrl -OutFile $TempZip -UseBasicParsing
    
    Write-Host "Extraindo arquivos..." -ForegroundColor Yellow
    
    # Extrair
    Expand-Archive -Path $TempZip -DestinationPath $env:APPDATA -Force
    
    # Limpar
    Remove-Item $TempZip -Force
    
    Write-Host ""
    Write-Host "=== Instalação Concluída com Sucesso! ===" -ForegroundColor Green
    Write-Host "Iniciando NetAudit..." -ForegroundColor Green
    Write-Host ""
    
    # Executar
    Start-Process $ExePath -WorkingDirectory $InstallDir
    
} catch {
    Write-Host ""
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Verifique sua conexão com a internet e tente novamente." -ForegroundColor Yellow
    pause
    exit 1
}
