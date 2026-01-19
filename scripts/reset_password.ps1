param (
    [string]$Server,
    [string]$Domain,
    [string]$AdminUser,
    [System.Security.SecureString]$AdminPass,
    [string]$TargetUsername,
    [string]$NewPassword
)

try {
    # Monta o nome de usuário completo para autenticação
    $adminFull = "$Domain\$AdminUser"
    
    # Cria o objeto de contexto principal para busca
    $root = "LDAP://$Server/DC=" + $Domain.Replace(".", ",DC=")
    
    # DirectoryEntry não aceita SecureString diretamente, convertemos para plain texto no momento do bind
    $plainAdminPass = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($AdminPass))
    $entry = New-Object DirectoryServices.DirectoryEntry($root, $adminFull, $plainAdminPass)
    $searcher = New-Object DirectoryServices.DirectorySearcher($entry)
    $searcher.Filter = "(sAMAccountName=$TargetUsername)"
    
    $result = $searcher.FindOne()
    
    if ($null -eq $result) {
        Write-Output "ERROR: Usuário '$TargetUsername' não encontrado."
        exit 1
    }
    
    # Obtém o objeto DirectoryEntry do usuário para alteração
    $userEntry = $result.GetDirectoryEntry()
    
    # Define a nova senha
    $userEntry.Invoke("SetPassword", @($NewPassword))
    
    # Desbloqueia a conta (opcional, mas recomendado ao resetar)
    if ($userEntry.Properties.Contains("lockoutTime")) {
        $userEntry.Properties["lockoutTime"].Value = 0
    }
    
    # Salva as alterações
    $userEntry.CommitChanges()
    
    Write-Output "SUCCESS: Senha alterada com sucesso."
    exit 0

}
catch {
    $err = $_.Exception.Message
    if ($err -match "Exception calling") {
        # Tenta extrair a mensagem interna se possível
        Write-Output "ERROR: O servidor recusou a senha (Política de Complexidade ou Permissão)."
    }
    else {
        Write-Output "ERROR: $err"
    }
    exit 1
}
