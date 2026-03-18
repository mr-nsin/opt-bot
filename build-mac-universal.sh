#!/usr/bin/env bash
# Build QuantDrift as a universal macOS app (runs on both Intel and Apple Silicon).
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Ensure Rust has both targets for universal build
echo "==> Ensuring Rust targets (aarch64 + x86_64)..."
rustup target add x86_64-apple-darwin 2>/dev/null || true
rustup target add aarch64-apple-darwin 2>/dev/null || true

# Build trading-engine for BOTH architectures
echo ""
node scripts/prebuild-trading-engine-universal.mjs

# Verify universal sidecar exists (created by prebuild script)
if [[ ! -f "$ROOT/src-tauri/binaries/trading-engine-universal-apple-darwin" ]]; then
  echo ""
  echo "ERROR: trading-engine-universal-apple-darwin not found."
  echo "  The prebuild needs x86_64 Python 3.12 (pandas_ta has no wheel for 3.13 on x86_64)."
  echo "  Install Intel Homebrew + Python 3.12:"
  echo "    arch -x86_64 /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  echo "    arch -x86_64 /usr/local/bin/brew install python@3.12"
  echo "  Remove stale venv and retry: rm -rf trading-engine/.venv_x64 && npm run build:mac:universal"
  echo ""
  echo "  Or use single-arch build: npm run build:mac"
  exit 1
fi

echo ""
echo "==> Building Tauri universal app..."
CI=false npx tauri build --target universal-apple-darwin

BUNDLE="$ROOT/src-tauri/target/universal-apple-darwin/release/bundle/macos"
APP="$BUNDLE/QuantDrift.app"
DMG_DIR="$ROOT/src-tauri/target/universal-apple-darwin/release/bundle/dmg"

# universal-apple-darwin puts output in target/universal-apple-darwin
if [[ ! -d "$BUNDLE" ]]; then
  BUNDLE="$ROOT/src-tauri/target/release/bundle/macos"
  APP="$BUNDLE/QuantDrift.app"
fi

# Ensure binaries are executable (prevents "can't be opened" when app is zipped/transferred)
if [[ -d "$APP" ]]; then
  chmod +x "$APP/Contents/MacOS/opt-bot" "$APP/Contents/MacOS/trading-engine" 2>/dev/null || true
fi

echo ""
echo "Build complete."
if [[ -d "$APP" ]]; then
  echo "  App:  $APP"
  echo "  Run:  open \"$APP\""
fi
if [[ -d "$DMG_DIR" ]]; then
  DMG=$(ls "$DMG_DIR"/*.dmg 2>/dev/null | head -1)
  if [[ -n "$DMG" ]]; then
    echo "  DMG:  $DMG"
  fi
fi
