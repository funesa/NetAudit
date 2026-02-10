param (
    [string]$Subnet = ""
)

$ErrorActionPreference = 'SilentlyContinue'

# Safely expand subnet to IP list
function Get-IPsInSubnet {
    param ([string]$Cidr)
    try {
        if ($Cidr -notlike "*/*") { return @($Cidr) }
        $ipPart, $maskPart = $Cidr.Split('/')
        $ipObj = [System.Net.IPAddress]::Parse($ipPart)
        $maskBits = [int]$maskPart
        
        $ipBytes = $ipObj.GetAddressBytes()
        if ([System.BitConverter]::IsLittleEndian) { [Array]::Reverse($ipBytes) }
        $ipInt = [System.BitConverter]::ToUInt32($ipBytes, 0)
        
        $maskInt = [uint32]([math]::Pow(2, 32) - [math]::Pow(2, (32 - $maskBits)))
        $networkInt = $ipInt -band $maskInt
        $numHosts = [uint32]([math]::Pow(2, (32 - $maskBits)))
        
        $resultList = New-Object System.Collections.Generic.List[string]
        
        # Limit to reasonable range (max /22)
        $limit = [math]::Min(1024, $numHosts - 1)
        
        for ($i = 1; $i -lt $limit; $i++) {
            $currentInt = $networkInt + $i
            $currentBytes = [System.BitConverter]::GetBytes([uint32]$currentInt)
            if ([System.BitConverter]::IsLittleEndian) { [Array]::Reverse($currentBytes) }
            $ipStr = ([System.Net.IPAddress]::new($currentBytes)).IPAddressToString
            $null = $resultList.Add($ipStr)
        }
        return $resultList
    }
    catch {
        return @($Cidr)
    }
}

$ips = Get-IPsInSubnet -Cidr $Subnet
$foundResults = New-Object System.Collections.Generic.List[PSCustomObject]

if ($ips -and $ips.Count -gt 0) {
    # Parallel Ping using Runspaces
    $runspacePool = [runspacefactory]::CreateRunspacePool(1, 40)
    $runspacePool.Open()
    $jobs = @()

    foreach ($target in $ips) {
        $ps = [powershell]::Create()
        $ps.RunspacePool = $runspacePool
        $ps.AddScript({
                param($ip)
                if (Test-Connection -ComputerName $ip -Count 1 -Quiet -BufferSize 16) {
                    try {
                        $hostName = [System.Net.Dns]::GetHostEntry($ip).HostName
                    }
                    catch {
                        $hostName = ""
                    }
                    return [PSCustomObject]@{
                        IP       = $ip
                        Status   = "Online"
                        Hostname = $hostName
                    }
                }
            }).AddArgument($target) | Out-Null
        
        $jobs += @{ Pipe = $ps; AsyncDetails = $ps.BeginInvoke() }
    }

    foreach ($job in $jobs) {
        try {
            $res = $job.Pipe.EndInvoke($job.AsyncDetails)
            if ($res) { 
                # $res is a collection of 1 item
                $null = $foundResults.Add($res[0]) 
            }
        }
        catch {}
        $job.Pipe.Dispose()
    }

    $runspacePool.Close()
}

# FINAL OUTPUT ONLY - Ensure clean JSON array
if ($foundResults.Count -eq 0) {
    Write-Output "[]"
}
else {
    $foundResults | ConvertTo-Json -Compress | Write-Output
}
