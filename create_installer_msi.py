"""
Cria o instalador MSI profissional do NetAudit
Usa Python MSI tools sem precisar do WiX instalado
"""
import os
import sys
from pathlib import Path

print("=" * 60)
print("  CRIADOR DE INSTALADOR MSI - NetAudit Enterprise")
print("=" * 60)
print()

# Para criar um MSI real, vamos usar uma abordagem alternativa:
# Criar um executável que usa NSIS (instalador profissional)

NSIS_SCRIPT = r"""
!define PRODUCT_NAME "NetAudit Enterprise"
!define PRODUCT_VERSION "2026.1.14"
!define PRODUCT_PUBLISHER "FUNESA"
!define PRODUCT_WEB_SITE "https://github.com/funesa/NetAudit"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\NetAudit_System.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor lzma

!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.rtf"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "PortugueseBR"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "NetAudit_Setup.exe"
InstallDir "$PROGRAMFILES\NetAudit Enterprise"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

Section "Principal" SEC01
  SetOutPath "$INSTDIR\NetAudit_System"
  SetOverwrite ifnewer
  File /r "dist\NetAudit_System\*.*"
  
  CreateDirectory "$SMPROGRAMS\NetAudit Enterprise"
  CreateShortCut "$SMPROGRAMS\NetAudit Enterprise\NetAudit Enterprise.lnk" "$INSTDIR\NetAudit_System\NetAudit_System.exe"
  CreateShortCut "$DESKTOP\NetAudit Enterprise.lnk" "$INSTDIR\NetAudit_System\NetAudit_System.exe"
  
  WriteUninstaller "$INSTDIR\uninst.exe"
SectionEnd

Section Uninstall
  Delete "$INSTDIR\uninst.exe"
  Delete "$SMPROGRAMS\NetAudit Enterprise\*.*"
  Delete "$DESKTOP\NetAudit Enterprise.lnk"
  
  RMDir /r "$INSTDIR\NetAudit_System"
  RMDir /r "$SMPROGRAMS\NetAudit Enterprise"
  RMDir "$INSTDIR"
  
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
SectionEnd
"""

# Salvar script NSIS
with open("NetAudit.nsi", "w", encoding="utf-8") as f:
    f.write(NSIS_SCRIPT)

print("✅ Arquivo NetAudit.nsi criado!")
print()
print("=" * 60)
print("PRÓXIMOS PASSOS:")
print("=" * 60)
print()
print("Para criar o instalador MSI/EXE profissional, você tem 2 opções:")
print()
print("OPÇÃO 1 - NSIS (Recomendado):")
print("1. Baixe o NSIS: https://nsis.sourceforge.io/Download")
print("2. Instale o NSIS")
print("3. Clique com botão direito em 'NetAudit.nsi'")
print("4. Escolha 'Compile NSIS Script'")
print("5. Será gerado: NetAudit_Setup.exe")
print()
print("OPÇÃO 2 - WiX Toolset (MSI real):")
print("1. Baixe WiX: https://wixtoolset.org/releases/")
print("2. Instale o WiX Toolset")
print("3. Execute:")
print("   candle NetAudit.wxs")
print("   light -ext WixUIExtension NetAudit.wixobj")
print("4. Será gerado: NetAudit.msi")
print()
print("=" * 60)
print()
print("POR ENQUANTO, use o Install-NetAudit.bat que já funciona!")
print()
