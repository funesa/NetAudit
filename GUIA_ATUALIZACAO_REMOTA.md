# 🚀 GUIA DE ATUALIZAÇÃO REMOTA - NetAudit System

## Como Funciona o Sistema de Update Automático

O NetAudit agora possui um sistema de atualização automática. Toda vez que o cliente abre o programa, ele verifica se existe uma versão mais nova disponível.

---

## 📋 PASSO A PASSO PARA VOCÊ (Desenvolvedor)

### 1️⃣ Quando você fizer uma mudança no código:

```bash
# 1. Abra o arquivo launcher.py
# 2. Mude a linha VERSION para a próxima versão:
VERSION = "1.0.2"  # Era 1.0.1, agora é 1.0.2

# 3. Compile o novo executável:
python build_exe.py

# 4. O arquivo estará em: dist/NetAudit_System.exe
```

### 2️⃣ Hospede o executável na internet:

Você tem 3 opções:

#### OPÇÃO A: GitHub (GRÁTIS e RECOMENDADO)
1. Crie um repositório no GitHub (pode ser privado)
2. Faça upload do `NetAudit_System.exe` para o repositório
3. Clique no arquivo e depois em "Download"
4. Copie o link que aparece (será algo como):
   ```
   https://github.com/SEU_USUARIO/netaudit/raw/main/NetAudit_System.exe
   ```

#### OPÇÃO B: Google Drive
1. Faça upload do arquivo
2. Clique com botão direito > Compartilhar > Qualquer pessoa com o link
3. Copie o ID do arquivo (está na URL)
4. Use este formato:
   ```
   https://drive.google.com/uc?export=download&id=SEU_ID_AQUI
   ```

#### OPÇÃO C: Seu próprio servidor
1. Faça upload via FTP para seu site
2. Use o link direto:
   ```
   https://seusite.com.br/downloads/NetAudit_System.exe
   ```

### 3️⃣ Atualize o arquivo version.json:

```json
{
  "latest_version": "1.0.2",
  "download_url": "SEU_LINK_DO_PASSO_2_AQUI",
  "release_notes": "Descrição do que mudou"
}
```

### 4️⃣ Hospede o version.json na internet:

**GitHub (Recomendado):**
1. Faça upload do `version.json` no mesmo repositório
2. Clique no arquivo > "Raw"
3. Copie o link (será algo como):
   ```
   https://raw.githubusercontent.com/SEU_USUARIO/netaudit/main/version.json
   ```

### 5️⃣ Configure o updater.py:

Abra o arquivo `updater.py` e cole o link do version.json:

```python
UPDATE_URL = "https://raw.githubusercontent.com/SEU_USUARIO/netaudit/main/version.json"
```

### 6️⃣ Recompile UMA ÚLTIMA VEZ:

```bash
python build_exe.py
```

---

## ✅ PRONTO! A partir de agora:

1. **Cliente abre o programa** → Sistema verifica se tem update
2. **Se tiver versão nova** → Aparece uma janela perguntando se quer atualizar
3. **Cliente clica em SIM** → Download automático + Instalação + Reinicia
4. **Você nunca mais precisa mandar .exe manualmente!**

---

## 🔄 Fluxo de Atualização (Resumo):

```
VOCÊ FAZ MUDANÇA NO CÓDIGO
    ↓
Muda VERSION no launcher.py (ex: 1.0.2)
    ↓
Roda: python build_exe.py
    ↓
Faz upload do .exe para GitHub/Drive/Servidor
    ↓
Atualiza version.json com nova versão e link
    ↓
Faz upload do version.json
    ↓
PRONTO! Cliente recebe update automático na próxima vez que abrir
```

---

## 📝 Exemplo Prático:

**Arquivo version.json (no GitHub):**
```json
{
  "latest_version": "1.0.2",
  "download_url": "https://github.com/pofjunior/netaudit/raw/main/NetAudit_System.exe",
  "release_notes": "Correção de bugs no AD + Melhorias de performance"
}
```

**Arquivo updater.py:**
```python
UPDATE_URL = "https://raw.githubusercontent.com/pofjunior/netaudit/main/version.json"
```

---

## ⚠️ IMPORTANTE:

- **SEMPRE** mude a VERSION no `launcher.py` antes de compilar
- **SEMPRE** atualize o `version.json` depois de fazer upload do .exe
- O cliente precisa ter internet para receber updates
- O update só acontece quando o cliente **abre** o programa

---

## 🎯 Arquivos que você precisa hospedar:

1. `NetAudit_System.exe` (o executável)
2. `version.json` (arquivo de controle de versão)

**Só isso!** Simples e automático! 🚀
