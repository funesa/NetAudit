; ============================================
; NetAudit - Inno Setup Installer Script
; ============================================
; Versão: 3.0.0
; Descrição: Instalador profissional para NetAudit
; ============================================

#define MyAppName "NetAudit"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "FUNESA"
#define MyAppURL "http://172.23.51.50"
#define MyAppExeName "NetAudit.exe"
#define MyAppIcon "netaudit.ico"

[Setup]
; Informações básicas
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Diretórios
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Licença e saída
LicenseFile=license.txt
OutputDir=installer\Output
OutputBaseFilename=NetAudit-Setup
SetupIconFile={#MyAppIcon}

; Compressão
Compression=lzma2/max
SolidCompression=yes

; Privilégios e compatibilidade
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Visual
WizardStyle=modern
DisableWelcomePage=no
; Usando imagens padrão do Inno Setup

; Desinstalador
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Criar atalho na Barra de Tarefas"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
; Executável principal
Source: "dist\NetAudit.exe"; DestDir: "{app}"; Flags: ignoreversion

; Frontend (React build)
Source: "frontend\dist\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs

; Templates e Static (Flask)
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs

; Arquivos de configuração (vão para AppData)
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "netaudit.ico"; DestDir: "{app}"; Flags: ignoreversion

; NOTA: Arquivos de dados (DB, JSON) serão criados em %APPDATA%\NetAudit automaticamente

[Dirs]
; Criar diretório de dados do usuário
Name: "{userappdata}\NetAudit"; Permissions: users-full

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

; Atalho na Área de Trabalho
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"; Tasks: desktopicon

; Atalho na Barra de Tarefas
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Executar após instalação
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpar dados do usuário (opcional - comentado por segurança)
; Type: filesandordirs; Name: "{userappdata}\NetAudit"

[Code]
// Verificar se já existe uma instância rodando
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // Tentar fechar instâncias em execução
  if CheckForMutexes('NetAuditMutex') then
  begin
    if MsgBox('O NetAudit está em execução. Deseja fechá-lo e continuar a instalação?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Tentar fechar graciosamente
      Exec('taskkill', '/F /IM NetAudit.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(2000);
    end
    else
    begin
      Result := False;
      Exit;
    end;
  end;
  Result := True;
end;

// Mensagem customizada de conclusão
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Aqui você pode adicionar lógica pós-instalação se necessário
  end;
end;
