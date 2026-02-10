# 🚀 NetAudit - Quick Start para Deploy

## Build Rápido (3 Passos)

### 1️⃣ Executar Build Completo
```batch
build-complete.bat
```

### 2️⃣ Copiar SHA256 e Atualizar version.json
O script mostrará o SHA256. Copie e cole em `update-server\version.json`:
```json
{
  "sha256": "COLE_AQUI"
}
```

### 3️⃣ Copiar Instalador
```batch
copy installer\Output\NetAudit-Setup.exe update-server\releases\
```

## Iniciar Servidor de Updates
```batch
start-update-server.bat
```

## Resultado
- ✅ Instalador: `installer\Output\NetAudit-Setup.exe`
- ✅ Servidor: `http://172.23.51.50:8080`
- ✅ Atualizações automáticas funcionando

## Documentação Completa
Veja `DEPLOY_GUIDE.md` para detalhes completos.

---

## Estrutura de Arquivos Criados

```
NetAudit/
├── build-complete.bat              ← Build tudo
├── build-frontend.bat              ← Build só frontend
├── build-backend.bat               ← Build só backend
├── start-update-server.bat         ← Iniciar servidor
├── NetAudit-Installer.iss          ← Script Inno Setup
├── DEPLOY_GUIDE.md                 ← Guia completo
├── updater.py                      ← Sistema de updates (atualizado)
└── update-server/
    ├── server.py                   ← Servidor HTTP
    ├── version.json                ← Versão atual
    └── releases/                   ← Instaladores
```

## Requisitos
- Python 3.9+
- Node.js 18+
- PyInstaller (`pip install pyinstaller`)
- Inno Setup 6 ([Download](https://jrsoftware.org/isdl.php))
