# Guia de Deploy - NetAudit v2026.1.4

## 📦 Checklist de Deploy

### Pré-Deploy
- [x] Versão atualizada em `version.json` (2026.1.4)
- [x] Release notes criadas (`RELEASE_NOTES_v2026.1.4.md`)
- [x] Código testado localmente
- [x] Migração SQLite testada (253 dispositivos)
- [/] Build do executável em andamento
- [ ] Executável testado
- [ ] Commit e push para GitHub
- [ ] Upload do executável para GitHub Releases

### Deploy
- [ ] Criar tag v2026.1.4 no Git
- [ ] Fazer upload do executável
- [ ] Atualizar `version.json` no repositório
- [ ] Notificar clientes da atualização

---

## 🚀 Passos para Deploy

### 1. Finalizar Build

```bash
# O build está rodando via build_exe.py
# Aguardar conclusão...
# Arquivo gerado: dist/NetAudit_System.exe
```

### 2. Testar Executável

```bash
# Executar em ambiente limpo
cd dist
.\NetAudit_System.exe

# Verificar:
# - Sistema inicia corretamente
# - Migração automática funciona
# - .env é criado automaticamente
# - netaudit.db é criado
```

### 3. Commit das Mudanças

```bash
git add .
git commit -m "v2026.1.4 - MAJOR: Migração SQLite + Gestão Segura + Otimizações"
git tag v2026.1.4
git push origin master
git push origin v2026.1.4
```

### 4. Upload para GitHub Releases

```bash
# Usar upload_release.bat ou manual via GitHub web
# Arquivo: dist/NetAudit_System.exe
# Tag: v2026.1.4
# Título: NetAudit System v2026.1.4 - Major Update
# Descrição: Copiar de RELEASE_NOTES_v2026.1.4.md
```

### 5. Atualizar version.json no Repositório

```bash
# Já está atualizado localmente
# Fazer push para que clientes vejam a atualização
git push origin master
```

---

## 📋 Arquivos Modificados

### Novos Arquivos
- `models.py` - Modelos SQLAlchemy
- `database.py` - Configuração do banco
- `migrate_to_db.py` - Script de migração
- `.gitignore` - Proteção de arquivos
- `RELEASE_NOTES_v2026.1.4.md` - Notas de release
- `static/tables.css` - CSS consolidado

### Arquivos Modificados
- `version.json` - Versão 2026.1.4
- `requirements.txt` - SQLAlchemy + alembic
- `app.py` - load_dotenv()
- `scripts/get_failed_logins.ps1` - SecureString
- `scripts/get_ad_storage.ps1` - SecureString
- `scripts/get_ad_users.ps1` - SecureString
- `scripts/reset_password.ps1` - SecureString
- `scripts/audit_windows.ps1` - SecureString
- `ad_helper.py` - Calls com SecureString

### Arquivos Removidos
- `templates/dashboard_old_backup.html`
- `templates/dashboard_new.html`
- `static/table-fix.css`
- `static/table-boundaries.css`
- `static/table-responsive.css`

---

## ⚠️ Avisos Importantes

### Backup Automático
O sistema cria backup automático de `scan_history.json` durante a migração.
Não é necessário backup manual.

### Compatibilidade
Totalmente compatível com versões anteriores.
Clientes podem atualizar sem perder dados.

### Arquivo .env
Criado automaticamente se não existir.
Contém credenciais - NÃO deve ser commitado (protegido por .gitignore).

---

## 🧪 Testes Pós-Deploy

### Teste 1: Atualização Automática
1. Cliente com v2026.1.3 abre o sistema
2. Sistema detecta v2026.1.4 disponível
3. Download automático
4. Atualização bem-sucedida

### Teste 2: Instalação Limpa
1. Download do executável
2. Primeira execução
3. .env criado automaticamente
4. netaudit.db criado
5. Sistema funcional

### Teste 3: Migração de Dados
1. Cliente com scan_history.json
2. Primeira execução da v2026.1.4
3. Migração automática
4. Backup criado
5. Dados preservados

---

## 📊 Métricas de Sucesso

- [ ] 100% dos clientes atualizados sem erros
- [ ] 0 reports de perda de dados
- [ ] Migração automática funcionando
- [ ] Performance melhorada (queries 10x mais rápidas)

---

## 🆘 Rollback (Se Necessário)

### Reverter para v2026.1.3

```bash
# 1. Restaurar executável antigo
# 2. Restaurar version.json
git revert HEAD
git push origin master

# 3. Clientes podem usar backup JSON
# scan_history.json.migrated_YYYYMMDD_HHMMSS
```

---

## 📞 Suporte

Em caso de problemas durante deploy:
1. Verificar logs de build
2. Testar executável localmente
3. Validar upload no GitHub
4. Monitorar feedback dos clientes
