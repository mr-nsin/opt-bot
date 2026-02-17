@echo off
REM Set your license registry env vars here (same session = app will see them).
REM Replace with your actual values before running.

set "REGISTRY_URL=https://drive.google.com/uc?export=download&id=1_d6-xEbniM2MNqZu1JQtAxrUCsV8-rae"
set REGISTRY_LICENSE_PUBLIC_KEY_HEX=5a838c50f67a4abbf6c1136f1acf1e8ee630b25c62fa87cd4c16953cb552a821

REM Optional: use Node + Rust from PATH if not already there
set PATH=C:\Program Files\nodejs;%USERPROFILE%\.cargo\bin;%PATH%

cd /d "%~dp0"
npm run tauri:dev
