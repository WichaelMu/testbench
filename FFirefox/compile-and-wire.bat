@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem =======================
rem Config / Paths
rem =======================
set "ROOT=%~dp0"
for %%# in ("%ROOT:~,-1%") do set "ROOT=%%~f#\"

if not defined OUTDIR (
  set "OUTDIR=%USERPROFILE%\Documents\Programming\MPrograms\FF"
  if not exist "%OUTDIR%" set "OUTDIR=%LOCALAPPDATA%\MPrograms\FF"
)
set "TASK_NAME=FF"
set "APP_NAME=FF Link Router"
set "PROGID=FF.LinkRouter"

if not exist "%OUTDIR%" md "%OUTDIR%" 2>nul

echo(
echo === FF Build ===
echo Source: %ROOT%
echo OutDir: %OUTDIR%
echo Task:   %TASK_NAME%
echo App:    %APP_NAME%  (ProgID: %PROGID%)
echo(

rem =======================
rem Find csc.exe
rem =======================
set "CSC="
if defined CSC if exist "%CSC%" set "CSC=%CSC%"

if not defined CSC (
  for /f "delims=" %%P in ('where csc 2^>nul') do if not defined CSC set "CSC=%%~fP"
)

if not defined CSC (
  for /f "delims=" %%P in ('dir /b /s "%USERPROFILE%\*Microsoft.Net.Compilers*\tools\csc.exe" 2^>nul ^| sort /r') do (
    if not defined CSC set "CSC=%%~fP"
  )
)

if not defined CSC (
  for /f "delims=" %%P in ('dir /b /s "%WINDIR%\Microsoft.NET\Framework64\v4*"\csc.exe 2^>nul ^| sort /r') do (
    if not defined CSC set "CSC=%%~fP"
  )
)

if not defined CSC (
  for /f "delims=" %%P in ('dir /b /s "%WINDIR%\Microsoft.NET\Framework\v4*"\csc.exe 2^>nul ^| sort /r') do (
    if not defined CSC set "CSC=%%~fP"
  )
)

if not defined CSC (
  echo [ERROR] Could not find csc.exe. Install .NET Framework Developer Pack or Roslyn compilers.
  exit /b 1
)

echo Using C# compiler: %CSC%

rem =======================
rem Build (windowless)
rem =======================
pushd "%ROOT%" >nul

echo(
echo [1/3] Building FFFocusTracker.exe ...
"%CSC%" /nologo /optimize+ /platform:anycpu /define:WINDOWS,FW_WINDOWS ^
  /target:winexe ^
  /out:"%OUTDIR%\FFFocusTracker.exe" ^
  "%ROOT%FFFocusTracker.cs" "%ROOT%FFCommon.cs" ^
  /r:System.Management.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll
if errorlevel 1 goto :build_fail

echo [2/3] Building FFLinkRouter.exe ...
"%CSC%" /nologo /optimize+ /platform:anycpu /define:WINDOWS,FW_WINDOWS ^
  /target:winexe ^
  /out:"%OUTDIR%\FFLinkRouter.exe" ^
  "%ROOT%FFLinkRouter.cs" "%ROOT%FFCommon.cs" ^
  /r:System.Management.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll
if errorlevel 1 goto :build_fail

echo [3/3] Ensuring log/state directories ...
set "LOCALFF=%LOCALAPPDATA%\FF"
if not exist "%LOCALFF%\logs"  md "%LOCALFF%\logs"  2>nul
if not exist "%LOCALFF%\state" md "%LOCALFF%\state" 2>nul

popd >nul

echo(
echo Build OK:
echo   %OUTDIR%\FFFocusTracker.exe
echo   %OUTDIR%\FFLinkRouter.exe

rem =======================
rem Task Scheduler (logon)
rem =======================
echo(
echo Wiring Scheduled Task: %TASK_NAME%
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

schtasks /Create /TN "%TASK_NAME%" /TR "\"%OUTDIR%\FFFocusTracker.exe\"" /SC ONLOGON /RL HIGHEST /F >nul 2>&1
if errorlevel 1 (
  echo   (retry without highest privileges)
  schtasks /Create /TN "%TASK_NAME%" /TR "\"%OUTDIR%\FFFocusTracker.exe\"" /SC ONLOGON /F
)

schtasks /Run /TN "%TASK_NAME%" >nul 2>&1

rem =======================
rem Register as a browser-capable app (per-user, HKCU)
rem =======================
echo(
echo Registering Default Apps capabilities...

rem ProgID + open command
reg add "HKCU\Software\Classes\%PROGID%" /ve /d "%APP_NAME%" /f >nul
reg add "HKCU\Software\Classes\%PROGID%" /v "URL Protocol" /d "" /f >nul
reg add "HKCU\Software\Classes\%PROGID%\DefaultIcon" /ve /d "%%SystemRoot%%\\System32\\url.dll,0" /f >nul
reg add "HKCU\Software\Classes\%PROGID%\shell\open\command" /ve /d "\"%OUTDIR%\\FFLinkRouter.exe\" \"%%1\"" /f >nul

rem Capabilities
reg add "HKCU\Software\Classes\%PROGID%\Capabilities" /v "ApplicationName" /d "%APP_NAME%" /f >nul
reg add "HKCU\Software\Classes\%PROGID%\Capabilities" /v "ApplicationDescription" /d "Routes links to the last-focused Firefox profile" /f >nul
reg add "HKCU\Software\Classes\%PROGID%\Capabilities\URLAssociations" /v "http"  /d "%PROGID%" /f >nul
reg add "HKCU\Software\Classes\%PROGID%\Capabilities\URLAssociations" /v "https" /d "%PROGID%" /f >nul

rem Register application so it appears in Default Apps UI
reg add "HKCU\Software\RegisteredApplications" /v "%APP_NAME%" /d "Software\\Classes\\%PROGID%\\Capabilities" /f >nul

echo(
echo Windows requires you to confirm default handlers once.
echo Opening the Settings pages for HTTP/HTTPS now...
start "" ms-settings:defaultapps?filters=protocol&value=http
start "" ms-settings:defaultapps?filters=protocol&value=https

echo(
echo Done.
echo Test:  start "" "https://example.com"
echo Logs:  %LOCALAPPDATA%\FF\logs
exit /b 0

:build_fail
echo(
echo [ERROR] Build failed.
exit /b 1