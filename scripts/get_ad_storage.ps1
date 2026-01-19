# get_ad_storage.ps1 - monitoramento de discos dos servidores do domínio
# Lista todos os discos lógicos (Locais) dos servidores e espaço livre
# Suporta credenciais via parametros

param(
    [string]$User,
    [System.Security.SecureString]$Password
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Cria objeto de credencial se fornecido
$cred = $null
if (-not [string]::IsNullOrWhiteSpace($User) -and $null -ne $Password) {
    $cred = New-Object System.Management.Automation.PSCredential($User, $Password)
}

try {
    # 1. Obter servidores
    # Se tiver credencial e módulo AD, usa credencial
    $servers = @()
    try {
        if (Get-Command Get-ADComputer -ErrorAction SilentlyContinue) {
            $params = @{ Filter = 'OperatingSystem -like "*Server*"'; Properties = "OperatingSystem", "IPv4Address" }
            # Get-ADComputer geralmente usa a sessão atual, credential as vezes requer conexão explicita or drive
            # Vamos arriscar sem credential no Get-ADComputer (assumindo que o PC onde roda tem trust), 
            # ou se falhar, tenta ADSI. 
            $servers = Get-ADComputer @params | Select-Object Name, DNSHostName, OperatingSystem
        }
        else {
            # Fallback ADSI (O Searcher usa a credencial do processo atual ou pode ser configurado, 
            # mas ADSI com creds é mais chato no Powershell puro sem DirectoryEntry explicito.
            # Vamos manter o padrão para discovery, o foco da credencial é WMI que é o que falha pra Access Denied)
            $searcher = [adsisearcher]""
            $searcher.Filter = "(&(objectClass=computer)(operatingSystem=*Server*))"
            $searcher.PageSize = 200
            $servers = $searcher.FindAll() | ForEach-Object {
                @{
                    Name            = $_.Properties["name"][0]
                    DNSHostName     = $_.Properties["dNSHostName"][0]
                    OperatingSystem = if ($_.Properties.Contains("operatingSystem")) { $_.Properties["operatingSystem"][0] } else { "Unknown" }
                }
            }
        }
    }
    catch {
        # Se falhar discovery, tenta localhost apenas
        $servers = @(@{ Name = "localhost"; DNSHostName = "localhost" })
    }

    $allDisks = @()

    foreach ($srv in $servers) {
        $hostName = if ($srv.DNSHostName) { $srv.DNSHostName } else { $srv.Name }
        $os = if ($srv.OperatingSystem) { $srv.OperatingSystem } else { "N/A" }
        if (-not $hostName) { continue }

        # Verifica se é localhost para NÃO usar credenciais (WMI local não suporta creds)
        $isLocal = ($hostName -eq "localhost" -or $hostName -eq $env:COMPUTERNAME -or $hostName -eq "$($env:COMPUTERNAME).$($env:USERDNSDOMAIN)")
        
        try {
            $wmiParams = @{
                Class        = "Win32_LogicalDisk"
                ComputerName = $hostName
                Filter       = "DriveType=3"
                ErrorAction  = "Stop"
            }
            
            # Só adiciona credencial se NÃO for local e se a credencial existir
            if (-not $isLocal -and $cred) {
                $wmiParams["Credential"] = $cred
            }

            $disks = Get-WmiObject @wmiParams | Select-Object DeviceID, VolumeName, Size, FreeSpace

            foreach ($d in $disks) {
                $totalGB = [math]::Round($d.Size / 1GB, 2)
                $freeGB = [math]::Round($d.FreeSpace / 1GB, 2)
                $usedGB = [math]::Round($totalGB - $freeGB, 2)
                
                $pctUsed = 0
                if ($totalGB -gt 0) {
                    $pctUsed = [math]::Round(($usedGB / $totalGB) * 100, 1)
                }

                $allDisks += @{
                    Server  = $hostName.ToUpper()
                    OS      = $os
                    Drive   = $d.DeviceID
                    Label   = if ($d.VolumeName) { $d.VolumeName } else { "Local Disk" }
                    TotalGB = $totalGB
                    FreeGB  = $freeGB
                    UsedGB  = $usedGB
                    PctUsed = $pctUsed
                    Status  = "Online"
                }
            }
        }
        catch {
            $err = $_.Exception.Message
            # Tenta simplificar msg de erro
            if ($err -match "Access is denied") { $err = "Acesso Negado (Verifique Credenciais)" }
            if ($err -match "RPC server is unavailable") { $err = "Offline / Firewall bloqueando WMI" }

            $allDisks += @{
                Server  = $hostName.ToUpper()
                OS      = $os
                Drive   = "-"
                Label   = "-"
                TotalGB = 0
                FreeGB  = 0
                UsedGB  = 0
                PctUsed = 0
                Status  = "Offline"
                Error   = $err
            }
        }
    }

    $allDisks | ConvertTo-Json -Depth 3 -Compress

}
catch {
    # Retorna array vazio em caso de erro catastrófico para não quebrar JSON parse
    Write-Output "[]"
    exit 1
}
