@echo off
setlocal ENABLEDELAYEDEXPANSION

set SRC=%~dp0
set OUTDIR=%LOCALAPPDATA%\FF
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo === Building (MinGW-w64 g++) ===
echo Source: %SRC%
echo OutDir: %OUTDIR%

set CXXFLAGS=-O2 -DNDEBUG -std=c++17 -DFF_WINDOWS -I"%SRC%Headers"
set LDFLAGS_TRACKER=-lole32 -loleaut32 -lwbemuuid

rem Build FFCommon
g++ %CXXFLAGS% -c "%SRC%FFCommon.cpp" -o "%OUTDIR%\FFCommon.o" || goto :err

rem Build FFLinkRouter
g++ %CXXFLAGS% -c "%SRC%FFLinkRouter.cpp" -o "%OUTDIR%\FFLinkRouter.o" || goto :err
g++ -O2 -s -o "%OUTDIR%\FFLinkRouter.exe" "%OUTDIR%\FFCommon.o" "%OUTDIR%\FFLinkRouter.o" || goto :err

rem Build FFFocusTracker (Windows only)
g++ %CXXFLAGS% -c "%SRC%FFFocusTracker.cpp" -o "%OUTDIR%\FFFocusTracker.o" || goto :err
g++ -O2 -s -o "%OUTDIR%\FFFocusTracker.exe" "%OUTDIR%\FFFocusTracker.o" "%OUTDIR%\FFCommon.o" %LDFLAGS_TRACKER% || goto :err

echo.
echo Built:
echo   %OUTDIR%\FFLinkRouter.exe
echo   %OUTDIR%\FFFocusTracker.exe
exit /b 0

:err
echo [ERROR] Build failed.
exit /b 1
