# get_ad_shares.ps1 - Lista compartilhamentos SMB nos servidores do domínio AD
# Requer módulo Active Directory e acesso WMI/CIM aos servidores

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

try {
    # 1. Obter todos os computadores que são servidores (Windows Server)
    # Se não tiver comando AD disponível, usa ADSI
    
    $servers = @()
    try {
        if (Get-Command Get-ADComputer -ErrorAction SilentlyContinue) {
            $servers = Get-ADComputer -Filter 'OperatingSystem -like "*Server*"' -Properties OperatingSystem, IPv4Address | Select-Object Name, DNSHostName, IPv4Address, OperatingSystem
        } else {
            # Fallback ADSI
            $searcher = [adsisearcher]""
            $searcher.Filter = "(&(objectClass=computer)(operatingSystem=*Server*))"
            $searcher.PageSize = 200
            $servers = $searcher.FindAll() | ForEach-Object {
                 @{
                    Name = $_.Properties["name"][0]
                    DNSHostName = $_.Properties["dNSHostName"][0]
                    OperatingSystem = if($_.Properties.Contains("operatingSystem")) { $_.Properties["operatingSystem"][0] } else { "Unknown" }
                 }
            }
        }
    } catch {
        # Fallback local se estiver rodando no próprio DC ou não autenticado
        # Assume localhost
        $servers = @(@{ Name = "localhost"; DNSHostName = "localhost" })
    }

    $allShares = @()

    foreach ($srv in $servers) {
        $hostName = if ($srv.DNSHostName) { $srv.DNSHostName } else { $srv.Name }
        $os = if ($srv.OperatingSystem) { $srv.OperatingSystem } else { "N/A" }
        
        # Pular se o nome estiver vazio (pode acontecer em adsi bad result)
        if (-not $hostName) { continue }

        try {
            # Tenta listar shares via CIM (moderno) ou WMI (legado)
            # Win32_Share: Type=0 (Disk Drive)
            $shares = Get-WmiObject -Class Win32_Share -ComputerName $hostName -Filter "Type=0" -ErrorAction Stop | Select-Object Name, Path, Description
            
            foreach ($share in $shares) {
                # Ignorar shares administrativos ocultos (C$, ADMIN$, IPC$, NETLOGON, SYSVOL se quiser filtrar)
                # O usuário pediu "pastas de rede", geralmente dados.
                if ($share.Name.EndsWith('$')) { continue }
                if ($share.Name -eq "SYSVOL" -or $share.Name -eq "NETLOGON") { continue }
                
                $allShares += @{
                    Server = $hostName.ToUpper()
                    ShareName = $share.Name
                    Path = $share.Path
                    Description = if($share.Description) { $share.Description } else { "" }
                    UNCPath = "\\$($hostName)\$($share.Name)"
                    OS = $os
                    Status = "Online"
                }
            }
        } catch {
            # Se falhar conexão (firewall, offline), registra erro
            $err = $_.Exception.Message
            $allShares += @{
                Server = $hostName.ToUpper()
                ShareName = "N/A"
                Path = "N/A"
                Description = "Erro ao conectar: $err"
                UNCPath = "N/A"
                OS = $os
                Status = "Offline/Acesso Negado"
            }
        }
    }

    $allShares | ConvertTo-Json -Depth 3 -Compress

} catch {
    Write-Output "[]"
    exit 1
}
