@echo off
schtasks /Delete /TN "FFFocusTracker" /F >NUL 2>&1

reg delete "HKCU\Software\Classes\FF.LinkRouter\shell\open\command" /f >NUL 2>&1
reg delete "HKCU\Software\Classes\FF.LinkRouter\shell\open" /f >NUL 2>&1
reg delete "HKCU\Software\Classes\FF.LinkRouter\shell" /f >NUL 2>&1
reg delete "HKCU\Software\Classes\FF.LinkRouter" /f >NUL 2>&1

set OUTDIR=%LOCALAPPDATA%\FF
del /Q "%OUTDIR%\FFLinkRouter.exe" >NUL 2>&1
del /Q "%OUTDIR%\FFFocusTracker.exe" >NUL 2>&1
del /Q "%OUTDIR%\FFCommon.o" "%OUTDIR%\FFLinkRouter.o" "%OUTDIR%\FFFocusTracker.o" >NUL 2>&1

echo Uninstalled tracker + router. (Logs and JSON remain in %LOCALAPPDATA%\FF)
