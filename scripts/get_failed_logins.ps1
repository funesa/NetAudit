# get_failed_logins.ps1 - Coleta tentativas de login falhadas dos servidores do domínio
# Event ID 4625 = Failed Login Attempt

param(
    [string]$User,
    # Usa SecureString para proteger a senha em memória e evitar exposição em logs
    [System.Security.SecureString]$Password,
    [int]$Hours = 24  # Últimas 24 horas por padrão
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Cria credencial se fornecida
$cred = $null
if (-not [string]::IsNullOrWhiteSpace($User) -and $null -ne $Password) {
    $cred = New-Object System.Management.Automation.PSCredential($User, $Password)
}

try {
    # 1. Obter Domain Controllers e Servidores
    $servers = @()
    try {
        if (Get-Command Get-ADComputer -ErrorAction SilentlyContinue) {
            # Pegar DCs e Servidores
            $dcs = Get-ADDomainController -Filter * | Select-Object -ExpandProperty HostName
            $servers += $dcs
            
            # Adicionar outros servidores importantes
            $otherServers = Get-ADComputer -Filter 'OperatingSystem -like "*Server*"' -Properties OperatingSystem | 
            Select-Object -ExpandProperty DNSHostName -First 5
            $servers += $otherServers
        }
        else {
            # Fallback: usar localhost
            $servers = @($env:COMPUTERNAME)
        }
    }
    catch {
        $servers = @($env:COMPUTERNAME)
    }

    $allFailedLogins = @()
    $startTime = (Get-Date).AddHours(-$Hours)

    foreach ($srv in $servers) {
        if (-not $srv) { continue }
        
        try {
            # Parâmetros para Get-WinEvent
            $filterHash = @{
                LogName   = 'Security'
                ID        = 4625  # Failed login
                StartTime = $startTime
            }

            $events = $null
            if ($cred -and $srv -ne $env:COMPUTERNAME) {
                $events = Get-WinEvent -ComputerName $srv -FilterHashtable $filterHash -Credential $cred -ErrorAction Stop -MaxEvents 100
            }
            else {
                $events = Get-WinEvent -ComputerName $srv -FilterHashtable $filterHash -ErrorAction Stop -MaxEvents 100
            }

            foreach ($evt in $events) {
                # Parse XML para extrair detalhes
                $xml = [xml]$evt.ToXml()
                $eventData = $xml.Event.EventData.Data
                
                # Extrair informações relevantes
                $targetUser = ($eventData | Where-Object { $_.Name -eq 'TargetUserName' }).'#text'
                $targetDomain = ($eventData | Where-Object { $_.Name -eq 'TargetDomainName' }).'#text'
                $workstation = ($eventData | Where-Object { $_.Name -eq 'WorkstationName' }).'#text'
                $ipAddress = ($eventData | Where-Object { $_.Name -eq 'IpAddress' }).'#text'
                $logonType = ($eventData | Where-Object { $_.Name -eq 'LogonType' }).'#text'
                $failureReason = ($eventData | Where-Object { $_.Name -eq 'SubStatus' }).'#text'

                # Traduzir código de falha
                $reasonText = switch ($failureReason) {
                    "0xC0000064" { "Usuário não existe" }
                    "0xC000006A" { "Senha incorreta" }
                    "0xC0000234" { "Conta bloqueada" }
                    "0xC0000072" { "Conta desabilitada" }
                    "0xC000006F" { "Fora do horário permitido" }
                    "0xC0000070" { "Restrição de estação de trabalho" }
                    "0xC0000193" { "Conta expirada" }
                    "0xC0000071" { "Senha expirada" }
                    default { "Outro motivo ($failureReason)" }
                }

                # Traduzir tipo de logon
                $logonTypeText = switch ($logonType) {
                    "2" { "Interativo (Console)" }
                    "3" { "Rede (SMB/RDP)" }
                    "4" { "Batch" }
                    "5" { "Serviço" }
                    "7" { "Unlock" }
                    "8" { "NetworkCleartext" }
                    "10" { "RemoteInteractive (RDP)" }
                    "11" { "CachedInteractive" }
                    default { "Tipo $logonType" }
                }

                $allFailedLogins += @{
                    Server        = $srv.ToUpper()
                    Timestamp     = $evt.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
                    Username      = "$targetDomain\$targetUser"
                    Workstation   = $workstation
                    IPAddress     = $ipAddress
                    LogonType     = $logonTypeText
                    FailureReason = $reasonText
                    EventID       = $evt.Id
                }
            }
        }
        catch {
            # Se falhar ao acessar logs, registra erro mas continua
            Write-Warning "Erro ao acessar logs de $srv : $($_.Exception.Message)"
        }
    }

    # Ordenar por timestamp (mais recente primeiro)
    $allFailedLogins = $allFailedLogins | Sort-Object -Property Timestamp -Descending

    $allFailedLogins | ConvertTo-Json -Depth 3 -Compress

}
catch {
    Write-Output "[]"
    exit 1
}
