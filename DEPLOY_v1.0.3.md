# 🚀 GUIA RÁPIDO - ENVIAR ATUALIZAÇÃO PARA O CLIENTE

## ✅ VERSÃO 1.0.3 - PRONTA PARA DEPLOY!

### 📦 Arquivos Prontos:
- ✅ `dist/NetAudit_System.exe` (Versão 1.0.3 com Wizard)
- ✅ `version.json` (Atualizado)

---

## 📋 PASSO A PASSO - UPLOAD NO GITHUB

### 1️⃣ Acesse o repositório:
```
https://github.com/funesa/NetAudit
```

### 2️⃣ Faça upload dos arquivos:

**Opção A: Via Interface Web (Mais Fácil)**

1. Clique em **"Add file"** → **"Upload files"**
2. Arraste estes 2 arquivos:
   - `c:\Users\POFJunior\Desktop\SCAN2026\dist\NetAudit_System.exe`
   - `c:\Users\POFJunior\Desktop\SCAN2026\version.json`
3. Na mensagem de commit, escreva:
   ```
   Release v1.0.3 - Wizard de Boas-Vindas
   ```
4. Clique em **"Commit changes"**

**Opção B: Via Git Command Line (Se preferir)**

```bash
cd c:\Users\POFJunior\Desktop\SCAN2026

# Inicializar repositório (se ainda não fez)
git init
git remote add origin https://github.com/funesa/NetAudit.git

# Adicionar arquivos
git add dist/NetAudit_System.exe
git add version.json

# Commit
git commit -m "Release v1.0.3 - Wizard de Boas-Vindas"

# Enviar para GitHub
git push origin main
```

---

## 🎯 O QUE ACONTECE DEPOIS DO UPLOAD:

1. ✅ **Cliente abre o NetAudit** (versão antiga 1.0.2)
2. ✅ **Sistema detecta** nova versão 1.0.3 disponível
3. ✅ **Aparece janela:** "Nova versão disponível! Deseja atualizar?"
4. ✅ **Cliente clica em SIM** → Download automático + Instalação
5. ✅ **Sistema reinicia** com a versão 1.0.3
6. ✅ **Wizard aparece** no primeiro login do usuário master!

---

## 🆕 NOVIDADES DA VERSÃO 1.0.3:

### ✨ Wizard de Boas-Vindas Interativo
- Apresentação visual do sistema
- Configuração guiada de Active Directory
- Configuração guiada de Helpdesk (GLPI)
- Design moderno com animações suaves
- Só aparece no primeiro acesso

### 🔧 Correções Anteriores (já incluídas):
- Scripts PowerShell invisíveis (sem janelas aparecendo)
- Login via Active Directory habilitado
- Todos os scripts incluídos no executável
- Sistema de atualização remota funcional

---

## ⚠️ IMPORTANTE:

**Depois de fazer o upload no GitHub:**

1. Teste se os links estão funcionando:
   - `https://github.com/funesa/NetAudit/raw/main/NetAudit_System.exe`
   - `https://raw.githubusercontent.com/funesa/NetAudit/main/version.json`

2. Se os links funcionarem, o cliente receberá a atualização automaticamente!

---

## 🎉 PRONTO!

A partir de agora, **NUNCA MAIS** você precisa enviar executável manualmente!

Toda vez que você quiser atualizar:
1. Mude a versão no código
2. Compile: `python build_exe.py`
3. Faça upload no GitHub
4. Cliente recebe automaticamente! 🚀

---

**Data de compilação:** 2026-01-15 16:33
**Versão:** 1.0.3
**Status:** ✅ PRONTO PARA DEPLOY
