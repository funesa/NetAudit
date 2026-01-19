# NetAudit Enterprise - Script de Build Limpo
# Este script garante que nenhum dado de teste seja incluído no executável final.

echo ">>> [BUILD] Iniciando processo de build limpo..."

# 1. Limpeza de pastas de build anteriores
if (Test-Path "build") { 
    echo ">>> [CLEAN] Removendo pasta /build..."
    Remove-Item -Recurse -Force build 
}
if (Test-Path "dist") { 
    echo ">>> [CLEAN] Removendo pasta /dist..."
    Remove-Item -Recurse -Force dist 
}

# 2. Garantia de ausência de arquivos de dados em pastas que serão embutidas
echo ">>> [AUDIT] Verificando pastas embutidas (static, templates, scripts)..."
$folders = @("static", "templates", "scripts")
foreach ($folder in $folders) {
    if (Test-Path $folder) {
        # Remove arquivos .json ou .log que possam ter sido criados por engano nessas pastas
        Get-ChildItem -Path $folder -Filter "*.json" -Recurse | Remove-Item -Force
        Get-ChildItem -Path $folder -Filter "*.log" -Recurse | Remove-Item -Force
        Get-ChildItem -Path $folder -Filter "test_*" -Recurse | Remove-Item -Force
    }
}

# 3. Execução do PyInstaller usando o arquivo .spec seguro
# O arquivo .spec já está configurado para NÃO incluir arquivos .json da raiz.
echo ">>> [COMPILE] Gerando executável com PyInstaller..."
pyinstaller --clean --noconfirm NetAudit_Server_Secure.spec

if ($LASTEXITCODE -eq 0) {
    echo ""
    echo "==========================================================="
    echo "   BUILD CONCLUÍDO COM SUCESSO E 100% LIMPO              "
    echo "==========================================================="
    echo "O executável está em: dist\NetAudit_Server_Secure"
    echo "Lembre-se: O sistema iniciará em 'Factory Reset' no cliente."
} else {
    echo "!!! [ERROR] Falha na compilação."
    exit $LASTEXITCODE
}
