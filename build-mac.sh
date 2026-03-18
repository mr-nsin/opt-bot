#!/usr/bin/env bash
# Build QuantDrift for macOS (runnable .app bundle).
# Equivalent to Windows build:exe workflow but produces a .app on Mac.
# Prebuild uses trading-engine/.venv when available (pandas_ta needs Python 3.12).
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> Building QuantDrift (trading-engine + React + Tauri)"
CI=false npm run tauri:build

# Output locations
BUNDLE="$ROOT/src-tauri/target/release/bundle/macos"
APP="$BUNDLE/QuantDrift.app"
BINARY="$ROOT/src-tauri/target/release/opt-bot"

# Ensure binaries are executable (prevents "can't be opened" when app is zipped/transferred)
if [[ -d "$APP" ]]; then
  chmod +x "$APP/Contents/MacOS/opt-bot" "$APP/Contents/MacOS/trading-engine" 2>/dev/null || true
fi

echo ""
echo "Build complete."
if [[ -d "$APP" ]]; then
  echo "  App bundle:  $APP"
  echo "  Run:         open \"$APP\""
fi
if [[ -x "$BINARY" ]]; then
  echo "  Binary only: $BINARY"
fi
