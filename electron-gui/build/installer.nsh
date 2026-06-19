# Disable NSIS self integrity check so the installer won't abort with
# "Installer integrity check has failed" if AV or a bad download alters bytes.
# NOTE: this only affects the installer exe. The per-build uninstaller is
# generated separately and inherits NSIS defaults; a corrupted uninstaller
# must be removed manually (rm the install dir + registry uninstall entry).
CRCCheck off

# Defensive: fall back to product name if the macro isn't injected by this
# electron-builder version, so CreateShortCut never breaks the build.
!ifndef APP_DESCRIPTION
  !define APP_DESCRIPTION "${PRODUCT_NAME}"
!endif

!macro customInstall
  !ifndef DO_NOT_CREATE_START_MENU_SHORTCUT
    !ifdef MENU_FILENAME
      CreateDirectory "$SMPROGRAMS\${MENU_FILENAME}"
    !endif

    Delete "$newStartMenuLink"
    CreateShortCut "$newStartMenuLink" "$appExe" "" "$appExe" 0 "" "" "${APP_DESCRIPTION}"
    ClearErrors
    WinShell::SetLnkAUMI "$newStartMenuLink" "${APP_ID}"
  !endif

  # Finish-page launch must not depend on a stale shortcut from an older install.
  StrCpy $launchLink "$appExe"
!macroend
