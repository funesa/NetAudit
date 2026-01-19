param (
    [Parameter(Mandatory)]
    [string]$Ip,

    [string]$User,
    [System.Security.SecureString]$Password,

    [int]$TimeoutMs = 3000,
    [switch]$TryFallback
)

$ErrorActionPreference = 'Stop'

$result = [ordered]@{
    ip       = $Ip
    online   = $false
    hostname = 'N/A'
    os       = 'N/A'
    version  = 'N/A'
    build    = 'N/A'
    model    = 'N/A'
    vendor   = 'N/A'
    ramGB    = 'N/A'
    cpu      = 'N/A'
    uptime   = 'N/A'
    user     = 'N/A'
    bios     = 'N/A'
    macs     = @()
    nics     = @()
    shares   = @()
    disks    = @()
    services = @()
    errors   = @()
}

# 1) Ping rápido
if (-not (Test-Connection -ComputerName $Ip -Count 1 -Quiet)) {
    $result.errors += 'Host não responde a ping'
    $result | ConvertTo-Json -Compress
    return
}
$result.online = $true

# 2) Hostname via DNS
try { $result.hostname = ([System.Net.Dns]::GetHostEntry($Ip)).HostName } catch {}

# 3) Configura Credenciais se fornecidas
$credential = $null
if ($User -and $Password) {
    $credential = New-Object System.Management.Automation.PSCredential($User, $Password)
}

# 4) Tenta CIM via WSMan
$session = $null
try {
    $opt = New-CimSessionOption -Protocol Wsman
    if ($credential) {
        $session = New-CimSession -ComputerName $Ip -SessionOption $opt -Credential $credential -ErrorAction Stop
    }
    else {
        $session = New-CimSession -ComputerName $Ip -SessionOption $opt -ErrorAction Stop
    }
}
catch {
    if ($TryFallback) {
        try {
            $opt = New-CimSessionOption -Protocol Dcom
            if ($credential) {
                $session = New-CimSession -ComputerName $Ip -SessionOption $opt -Credential $credential -ErrorAction Stop
            }
            else {
                $session = New-CimSession -ComputerName $Ip -SessionOption $opt -ErrorAction Stop
            }
        }
        catch {
            $result.errors += 'Falha ao criar CIM Session (WSMan/DCOM)'
        }
    }
    else {
        $result.errors += 'Falha ao criar CIM Session (WSMan)'
    }
}

if ($session) {
    try {
        # OS
        $os = Get-CimInstance Win32_OperatingSystem -CimSession $session
        $result.os = $os.Caption
        $result.version = $os.Version
        $result.build = $os.BuildNumber
        $result.uptime = $os.LastBootUpTime.ToString('dd/MM/yyyy HH:mm')

        # Computer System
        $cs = Get-CimInstance Win32_ComputerSystem -CimSession $session
        $result.model = $cs.Model
        $result.vendor = $cs.Manufacturer
        $result.user = $cs.UserName
        $result.ramGB = [Math]::Round($cs.TotalPhysicalMemory / 1GB, 2)

        # CPU
        $cpu = Get-CimInstance Win32_Processor -CimSession $session | Select-Object -First 1
        $result.cpu = "$($cpu.Name) | $($cpu.NumberOfCores) cores / $($cpu.NumberOfLogicalProcessors) threads"

        # BIOS
        $bios = Get-CimInstance Win32_BIOS -CimSession $session
        $result.bios = "$($bios.SMBIOSBIOSVersion) - $($bios.ReleaseDate.ToString('yyyy'))"

        # NICs
        $nics = Get-CimInstance Win32_NetworkAdapterConfiguration -CimSession $session | Where-Object { $_.IPEnabled }
        foreach ($n in $nics) {
            $result.macs += $n.MACAddress
            $result.nics += [ordered]@{
                description = $n.Description
                ip          = $n.IPAddress
                gateway     = $n.DefaultIPGateway
            }
        }

        # Shares
        Get-CimInstance Win32_Share -CimSession $session | Where-Object Type -eq 0 | ForEach-Object {
            $result.shares += "$($_.Name) ($($_.Path))"
        }

        # Disks
        Get-CimInstance Win32_LogicalDisk -CimSession $session | Where-Object DriveType -eq 3 | ForEach-Object {
            $size = [Math]::Round($_.Size / 1GB, 1)
            $free = [Math]::Round($_.FreeSpace / 1GB, 1)
            $used = [Math]::Round($size - $free, 1)
            $result.disks += "$($_.DeviceID) $used/$size GB"
        }

        # Serviços críticos
        Get-CimInstance Win32_Service -CimSession $session | Where-Object { $_.State -ne 'Running' } | Select-Object -First 10 | ForEach-Object {
            $result.services += "$($_.Name) [$($_.State)]"
        }

    }
    catch {
        $result.errors += $_.Exception.Message
    }
    finally {
        Remove-CimSession $session
    }
}

$result | ConvertTo-Json -Depth 5 -Compress
