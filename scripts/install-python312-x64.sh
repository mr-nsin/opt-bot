#!/usr/bin/env bash
# Install Python 3.12 for x86_64 (required for universal Mac build).
# Run this once, then: npm run build:mac:universal
#
# Option A: Python.org installer (recommended)
#   Opens the installer GUI. Click through to install. Creates:
#   /Library/Frameworks/Python.framework/Versions/3.12/
#
# Option B: Intel Homebrew (if you have it)
#   arch -x86_64 /usr/local/bin/brew install python@3.12
#
set -e
PKG="/tmp/python-3.12.7-macos11.pkg"
URL="https://www.python.org/ftp/python/3.12.7/python-3.12.7-macos11.pkg"

if [[ ! -f "$PKG" ]]; then
  echo "Downloading Python 3.12.7..."
  curl -sL -o "$PKG" "$URL"
fi

echo "Opening Python 3.12 installer..."
echo "  → Click through the dialogs to install"
echo "  → Choose 'Install for all users' (requires password)"
echo "  → After install, run: rm -rf trading-engine/.venv_x64 && npm run build:mac:universal"
open "$PKG"
