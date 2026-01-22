
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
