# NetAudit - Guia de Deploy e Atualização

## 📦 Preparação do Build

### Pré-requisitos

1. **Python 3.9+** instalado
2. **Node.js 18+** e npm instalados
3. **PyInstaller** instalado (`pip install pyinstaller`)
4. **Inno Setup 6** instalado ([Download](https://jrsoftware.org/isdl.php))

### Estrutura de Arquivos

```
NetAudit/
├── build-complete.bat          # Build completo (frontend + backend + instalador)
├── build-frontend.bat          # Build apenas frontend
├── build-backend.bat           # Build apenas backend
├── NetAudit-Installer.iss      # Script Inno Setup
├── start-update-server.bat     # Iniciar servidor de updates
└── update-server/
    ├── server.py               # Servidor HTTP de updates
    ├── version.json            # Informações de versão
    └── releases/               # Instaladores (.exe)
```

---

## 🚀 Processo de Build (Passo a Passo)

### 1. Build Completo

Execute o script automatizado:

```batch
build-complete.bat
```

Este script faz:
1. ✅ Compila o frontend React
2. ✅ Limpa builds anteriores
3. ✅ Compila o backend com PyInstaller
4. ✅ Integra frontend no executável
5. ✅ Gera instalador com Inno Setup
6. ✅ Calcula SHA256 do instalador

**Resultado**: `installer\Output\NetAudit-Setup.exe`

### 2. Atualizar version.json

Após o build, copie o SHA256 exibido e atualize:

**Arquivo**: `update-server\version.json`

```json
{
  "latest_version": "3.0.0",
  "download_url": "http://172.23.51.50:8080/updates/releases/NetAudit-Setup.exe",
  "sha256": "COLE_O_SHA256_AQUI",
  "release_notes": "Descrição das mudanças",
  "min_version": "1.0.0",
  "release_date": "2026-02-05"
}
```

### 3. Copiar Instalador para Servidor

```batch
copy installer\Output\NetAudit-Setup.exe update-server\releases\
```

---

## 🌐 Servidor de Atualizações

### Iniciar Servidor

```batch
start-update-server.bat
```

O servidor ficará disponível em:
- **URL Base**: `http://172.23.51.50:8080`
- **Version Check**: `http://172.23.51.50:8080/updates/version.json`
- **Download**: `http://172.23.51.50:8080/updates/releases/NetAudit-Setup.exe`

### Endpoints

| Endpoint | Descrição |
|----------|-----------|
| `GET /` | Página inicial do servidor |
| `GET /updates/version.json` | Informações da versão |
| `GET /updates/releases/<file>` | Download do instalador |
| `GET /updates/stats` | Estatísticas do servidor |

### Logs

Os logs ficam em: `update-server\update-server.log`

---

## 📝 Processo de Atualização

### Para Desenvolvedores

1. **Fazer mudanças no código**
2. **Incrementar versão** em `version.json`
3. **Executar build completo**: `build-complete.bat`
4. **Copiar SHA256** exibido no final
5. **Atualizar** `update-server\version.json` com novo SHA256
6. **Copiar instalador** para `update-server\releases\`
7. **Reiniciar servidor** de updates (se necessário)

### Para Usuários Finais

O NetAudit verifica atualizações automaticamente:
1. Ao iniciar a aplicação
2. Compara versão local com servidor
3. Se houver atualização, exibe notificação
4. Usuário clica para atualizar
5. Download automático
6. Instalação automática
7. Aplicação reinicia com nova versão

---

## 🔧 Instalação Manual (Inno Setup)

Se preferir compilar manualmente:

```batch
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" NetAudit-Installer.iss
```

---

## ✅ Checklist de Deploy

### Antes do Build
- [ ] Código testado e funcionando
- [ ] Versão incrementada em `version.json`
- [ ] Release notes atualizadas
- [ ] Frontend sem erros de lint
- [ ] Backend sem erros de lint

### Durante o Build
- [ ] Frontend compilou sem erros
- [ ] Backend compilou sem erros
- [ ] Instalador gerado com sucesso
- [ ] SHA256 calculado

### Após o Build
- [ ] SHA256 atualizado em `update-server\version.json`
- [ ] Instalador copiado para `update-server\releases\`
- [ ] Servidor de updates rodando
- [ ] Teste de instalação em máquina limpa
- [ ] Teste de atualização de versão anterior

---

## 🐛 Troubleshooting

### Erro: "Inno Setup não encontrado"
**Solução**: Instale o Inno Setup 6 de https://jrsoftware.org/isdl.php

### Erro: "PyInstaller não encontrado"
**Solução**: `pip install pyinstaller`

### Erro: "npm não encontrado"
**Solução**: Instale Node.js de https://nodejs.org

### Erro: "Build do frontend falhou"
**Solução**: 
```batch
cd frontend
npm install
npm run build
```

### Erro: "Servidor de updates não inicia"
**Solução**: Verifique se a porta 8080 está livre:
```batch
netstat -ano | findstr :8080
```

---

## 📊 Versionamento

Formato: `MAJOR.MINOR.PATCH`

- **MAJOR**: Mudanças incompatíveis
- **MINOR**: Novas funcionalidades compatíveis
- **PATCH**: Correções de bugs

Exemplo: `3.0.0` → `3.1.0` → `3.1.1`

---

## 🔐 Segurança

- ✅ Verificação SHA256 em todos os downloads
- ✅ Validação de cabeçalho MZ (executável Windows)
- ✅ Servidor local (sem exposição externa)
- ✅ Logs de todas as operações

---

## 📞 Suporte

Para problemas ou dúvidas:
- Verifique os logs em `update-server\update-server.log`
- Consulte este guia
- Entre em contato com a equipe de TI
