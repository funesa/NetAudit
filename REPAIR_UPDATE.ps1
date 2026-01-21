# Script de Reparo e Atualização Forçada do NetAudit System
# Use este script se a atualização automática falhar.

$ErrorActionPreference = "Stop"
$Url = "https://github.com/funesa/NetAudit/raw/master/dist/NetAudit_System.exe"
$AppName = "NetAudit_System.exe"
$CurrentLocation = Get-Location
$ExePath = Join-Path $CurrentLocation $AppName
$TempPath = Join-Path $CurrentLocation "NetAudit_System_New.exe"

Write-Host ">>> Iniciando Reparo do NetAudit System..." -ForegroundColor Cyan

# 1. Fechar o NetAudit se estiver rodando
Write-Host "1. Fechando processos antigos..." -ForegroundColor Yellow
try {
    Stop-Process -Name "NetAudit_System" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
catch {
    Write-Host "Nenhum processo em execução."
}

# 2. Baixar a nova versão
Write-Host "2. Baixando nova versão (v2026.1.8.1)..." -ForegroundColor Yellow
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $TempPath
    Write-Host "Download concluído com sucesso!" -ForegroundColor Green
}
catch {
    Write-Error "Falha no download: $_"
    exit
}

# 3. Substituir o arquivo
Write-Host "3. Substituindo executável..." -ForegroundColor Yellow
if (Test-Path $ExePath) {
    Remove-Item $ExePath -Force
}
Rename-Item -Path $TempPath -NewName $AppName -Force

Write-Host ">>> SUCESSO! O NetAudit foi atualizado para a versão mais recente." -ForegroundColor Green
Write-Host "Iniciando o sistema..."

# 4. Iniciar
Start-Process $ExePath
