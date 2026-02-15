@echo off
REM Build QuantDrift for Windows: trading-engine sidecar + Tauri app (exe + installer)
REM Run from project root. Requires: Node.js, Rust, Python 3.9-3.11, trading-engine deps (PyInstaller, ibapi, etc.)

setlocal
cd /d "%~dp0"

echo [1/2] Building trading-engine sidecar (trading-engine-x86_64-pc-windows-msvc.exe)...
python trading-engine\build.py
if errorlevel 1 (
    echo ERROR: trading-engine build failed. Install Python deps: cd trading-engine ^&^& pip install pyinstaller ibapi pandas numpy
    exit /b 1
)

echo.
echo [2/2] Building Tauri app (exe + installer)...
call npm run tauri build
if errorlevel 1 (
    echo ERROR: Tauri build failed.
    exit /b 1
)

echo.
echo Done. Installer and exe are in: src-tauri\target\release\bundle\
echo   - NSIS: nsis\QuantDrift_1.0.0_x64-setup.exe
echo   - Or run the .exe from msi\ or the bundle folder
endlocal
