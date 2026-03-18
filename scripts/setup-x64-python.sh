#!/usr/bin/env bash
# One-time setup for universal Mac build: install Python 3.12 for x86_64.
# pandas_ta has no wheel for Python 3.13 on x86_64, so we need 3.12.
#
# Option A: Intel Homebrew (requires sudo)
#   Run: ./scripts/setup-x64-python.sh
#
# Option B: Python.org installer (no script - manual)
#   1. Download https://www.python.org/ftp/python/3.12.7/python-3.12.7-macos11.pkg
#   2. Install (choose "Install for all users" or "Install for me only")
#   3. Creates /Library/Frameworks/Python.framework/Versions/3.12/
#
set -e
echo "==> Installing Intel Homebrew (for x86_64 Python 3.12)..."
echo "    This will prompt for your password."
arch -x86_64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

echo ""
echo "==> Installing Python 3.12 for x86_64..."
arch -x86_64 /usr/local/bin/brew install python@3.12

echo ""
echo "==> Done. Remove old venv and rebuild:"
echo "    rm -rf trading-engine/.venv_x64"
echo "    npm run build:mac:universal"
