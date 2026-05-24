@echo off
REM build_mds_onefile.bat - MDS Viewer compact build via Nuitka
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set PY=python
where %PY% >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python.exe not found in PATH
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Creating .venv
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv create failed
        exit /b 1
    )
)
set PY=.venv\Scripts\python.exe

if defined PIP_CLEAN (
    echo [CLEAN] purging pip cache
    %PY% -m pip cache purge
)

echo [DEPS] installing PySide6 + cryptography + Nuitka
%PY% -m pip install --upgrade pip
%PY% -m pip install PySide6 cryptography
%PY% -m pip install nuitka ordered-set zstandard
if errorlevel 1 (
    echo [ERROR] pip install failed
    exit /b 1
)

if not exist "data\archive" (
    echo [ERROR] data\archive\ folder missing
    exit /b 1
)
dir /b data\archive\*.enc >nul 2>&1
if errorlevel 1 (
    echo [ERROR] no .enc files in data\archive\
    exit /b 1
)

if exist "main.dist"          rmdir /s /q main.dist
if exist "main.build"         rmdir /s /q main.build
if exist "main.onefile-build" rmdir /s /q main.onefile-build
if exist "dist\MDS_Viewer.exe" del /q "dist\MDS_Viewer.exe"

set NUITKA_ARGS=--onefile
set NUITKA_ARGS=%NUITKA_ARGS% --windows-console-mode=disable
set NUITKA_ARGS=%NUITKA_ARGS% --enable-plugin=pyside6
set NUITKA_ARGS=%NUITKA_ARGS% --include-package=PySide6
set NUITKA_ARGS=%NUITKA_ARGS% --include-package=cryptography
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=db_crypto
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=report_generator
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=resource_helper
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=mds_dialog
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=qt_helper
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=lang
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=key_dialog
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=update_check
set NUITKA_ARGS=%NUITKA_ARGS% --include-module=app_paths
set NUITKA_ARGS=%NUITKA_ARGS% --noinclude-pytest-mode=nofollow
set NUITKA_ARGS=%NUITKA_ARGS% --noinclude-setuptools-mode=nofollow

set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=numpy
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=scipy
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=matplotlib
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=trimesh
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=pyvista
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=vtk
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PIL
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=numba
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=llvmlite
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=tkinter
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=qtpy
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PyQt5
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PyQt6
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide2
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=test
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=unittest
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=pytest

set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtWebEngineCore
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtWebEngineWidgets
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtWebEngineQuick
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtMultimedia
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtMultimediaWidgets
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtBluetooth
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtNetworkAuth
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtPositioning
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtQuick
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtQml
set NUITKA_ARGS=%NUITKA_ARGS% --nofollow-import-to=PySide6.QtCharts

set NUITKA_ARGS=%NUITKA_ARGS% --output-dir=dist
set NUITKA_ARGS=%NUITKA_ARGS% --output-filename=MDS_Viewer.exe
set NUITKA_ARGS=%NUITKA_ARGS% --remove-output

if defined BUILD_DEBUG (
    echo [INFO] BUILD_DEBUG=1
    set NUITKA_ARGS=!NUITKA_ARGS! --mingw64 --lto=no --jobs=%NUMBER_OF_PROCESSORS%
)

echo ================================================================
echo  MDS Viewer - Nuitka build (compact mode)
echo ================================================================

%PY% -m nuitka main.py %NUITKA_ARGS%
if errorlevel 1 (
    echo [ERROR] Nuitka build failed
    exit /b 1
)

if not exist "dist\MDS_Viewer.exe" (
    echo [ERROR] dist\MDS_Viewer.exe not produced
    exit /b 1
)

echo [BUNDLE] packaging
%PY% _build_bundle.py
if errorlevel 1 (
    echo [ERROR] bundle step failed
    exit /b 1
)

echo.
echo === Build complete ===
echo.
for %%f in ("dist\MDS_Viewer_*.zip") do echo   %%f
echo.
endlocal
