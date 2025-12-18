@echo off
setlocal
set OUTDIR=%LOCALAPPDATA%\FF
set LOG=%OUTDIR%\

if not exist "%OUTDIR%\FFLinkRouter.exe" (
  echo Build first (FFLinkRouter.exe missing).
  exit /b 1
)

if not exist "%OUTDIR%\FFFocusTracker.exe" (
  echo Build first (FFFocusTracker.exe missing).
  exit /b 1
)

echo %date% %time% Installer: Creating startup task for FFFocusTracker >> "%LOG%"

rem Create a scheduled task to run tracker at user logon
schtasks /Create /TN "FFFocusTracker" /TR "\"%OUTDIR%\FFFocusTracker.exe\"" /SC ONLOGON /RL LIMITED /F >NUL 2>&1

rem Register router as a URL handler ProgId (cannot force default for http/https due to Windows protections)
reg add "HKCU\Software\Classes\FF.LinkRouter" /ve /d "FF Link Router" /f >NUL
reg add "HKCU\Software\Classes\FF.LinkRouter" /v "URL Protocol" /d "" /f >NUL
reg add "HKCU\Software\Classes\FF.LinkRouter\shell\open\command" /ve /d "\"%OUTDIR%\FFLinkRouter.exe\" \"%%1\"" /f >NUL

echo.
echo Router is registered as 'FF.LinkRouter'. 
echo To make it the default for http/https, open Settings > Apps > Default apps and set web browser to FF Link Router (if shown).
echo If Windows blocks direct assignment, you can keep Firefox as default; FFLinkRouter is still callable manually or via file associations.
exit /b 0
