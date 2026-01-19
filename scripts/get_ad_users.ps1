param(
    [string]$Server,
    [string]$Domain,
    [string]$BaseDN,
    [string]$User,
    [System.Security.SecureString]$Password
)

$ErrorActionPreference = "Stop"
# Força saída em UTF-8 para não quebrar acentos no JSON
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

try {
    $searcher = $null
    
    # Se tiver credenciais e servidor, monta DirectoryEntry explícito
    if (-not [string]::IsNullOrWhiteSpace($Server) -and -not [string]::IsNullOrWhiteSpace($User)) {
        $path = "LDAP://$Server"
        if (-not [string]::IsNullOrWhiteSpace($BaseDN)) { $path += "/$BaseDN" }
        
        # Tenta formatos diferentes de bind
        $userFormats = @()
        if (-not $User.Contains("@") -and -not $User.Contains("\") -and -not [string]::IsNullOrWhiteSpace($Domain)) {
            $userFormats += "$User@$Domain"
            $userFormats += "$Domain\$User"
        }
        $userFormats += $User

        foreach ($uf in $userFormats) {
            try {
                # DirectoryEntry não aceita SecureString diretamente, convertemos para plain texto no momento do bind
                $plainPass = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password))
                $entry = New-Object System.DirectoryServices.DirectoryEntry($path, $uf, $plainPass)
                # Força o bind tentando acessar uma propriedade
                $test = $entry.NativeGuid
                $searcher = New-Object System.DirectoryServices.DirectorySearcher($entry)
                if ($null -ne $searcher) { break }
            }
            catch {
                continue
            }
        }
    } 
    
    if ($null -eq $searcher) {
        # Fallback para contexto atual
        $searcher = [adsisearcher]""
    }
    
    $searcher.Filter = "(&(objectClass=user)(objectCategory=person))"
    $searcher.PageSize = 1000

    # Propriedades para carregar (otimização)
    $props = @(
        "sAMAccountName", "displayName", "mail", "telephoneNumber", "mobile", 
        "department", "title", "company", "physicalDeliveryOfficeName", "manager",
        "description", "userAccountControl", "lastLogon", "lastLogonTimestamp", "whenCreated", "memberOf"
    )
    foreach ($p in $props) { $searcher.PropertiesToLoad.Add($p) | Out-Null }

    $results = $searcher.FindAll()
    $users = @()

    foreach ($res in $results) {
        $props = $res.Properties

        # Helper para pegar valor string seguro
        function Get-Val($name) {
            if ($props.Contains($name)) { return $props[$name][0].ToString() }
            return "N/A"
        }

        # Conversão de Data AD (FileTime)
        function Convert-ADDate($val) {
            try {
                if ($null -eq $val) { return $null }
                # AD retorna ComObject para LargeInteger, precisa converter
                $ticks = $val
                # Se for objeto COM, tenta pegar HighPart/LowPart (comum em ADSI puro)
                # Mas via DirectorySearcher geralmente vem como Long/Int64 direto ou Marshal
                if ($val -is [System.__ComObject]) {
                    # Fallback complexo, geralmente SEARCHER retorna o valor numérico ou collection
                    return $null
                }
                
                # O DirectorySearcher retorna Collection. O valor real é $props[$name][0]
                # Se o valor for Int64 (FileTime)
                [long]$ft = $val
                if ($ft -eq 0 -or $ft -gt 2650467743999999999) { return $null } # Validar ranges
                
                return [DateTime]::FromFileTime($ft).ToString("dd/MM/yyyy HH:mm")
            }
            catch {
                return $null
            }
        }

        # Lógica UserAccountControl
        $uac = 0
        if ($props.Contains("useraccountcontrol")) { $uac = [int]$props["useraccountcontrol"][0] }
        $status = "Ativo"
        $statusClass = "active"
        if ($uac -band 2) { 
            $status = "Desabilitado"
            $statusClass = "disabled"
        }
        elseif ($uac -band 16) {
            $status = "Bloqueado"
            $statusClass = "locked"
        }

        # Lógica Last Logon (Max entre lastLogon e lastLogonTimestamp)
        $lastLogon = 0
        if ($props.Contains("lastlogon")) { $lastLogon = [long]$props["lastlogon"][0] }
        
        $lastLogonTS = 0
        if ($props.Contains("lastlogontimestamp")) { $lastLogonTS = [long]$props["lastlogontimestamp"][0] }

        $finalLogon = "Nunca"
        $maxTs = 0
        if ($lastLogon -gt $lastLogonTS) { $maxTs = $lastLogon } else { $maxTs = $lastLogonTS }
        
        if ($maxTs -gt 0) {
            try {
                $finalLogon = [DateTime]::FromFileTime($maxTs).ToString("dd/MM/yyyy HH:mm")
            }
            catch { }
        }

        # Grupos
        $groups = @()
        if ($props.Contains("memberof")) {
            foreach ($g in $props["memberof"]) {
                # Extrai CN=Grupo,... -> Grupo
                $gName = ($g -split ",")[0] -replace "CN=", ""
                $groups += $gName
            }
        }

        # Manager
        $manager = "N/A"
        if ($props.Contains("manager")) {
            $manager = ($props["manager"][0] -split ",")[0] -replace "CN=", ""
        }

        # Objeto Usuário
        $userObj = @{
            username    = Get-Val "samaccountname"
            displayName = Get-Val "displayname"
            email       = Get-Val "mail"
            phone       = Get-Val "telephonenumber"
            mobile      = Get-Val "mobile"
            department  = Get-Val "department"
            title       = Get-Val "title"
            company     = Get-Val "company"
            office      = Get-Val "physicaldeliveryofficename"
            manager     = $manager
            description = Get-Val "description"
            status      = $status
            statusClass = $statusClass
            lastLogin   = $finalLogon
            created     = if ($props.Contains("whencreated")) { [DateTime]$props["whencreated"][0] | Get-Date -Format "dd/MM/yyyy" } else { "N/A" }
            groups      = $groups
        }
        $users += $userObj
    }

    # Retorna JSON puro
    $users | ConvertTo-Json -Depth 5 -Compress
}
catch {
    # Em caso de erro fatal, retorna array vazio JSON para não quebrar o Python
    Write-Output "[]"
    exit 1
}
