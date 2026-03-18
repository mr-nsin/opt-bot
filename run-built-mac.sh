#!/usr/bin/env bash
# Run the built QuantDrift.app with license registry env vars.
# Build first: npm run build:mac
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Universal build uses different output path
if [[ -d "$ROOT/src-tauri/target/universal-apple-darwin/release/bundle/macos" ]]; then
  APP="$ROOT/src-tauri/target/universal-apple-darwin/release/bundle/macos/QuantDrift.app"
else
  APP="$ROOT/src-tauri/target/release/bundle/macos/QuantDrift.app"
fi
BIN="$APP/Contents/MacOS/QuantDrift"

if [[ ! -x "$BIN" ]]; then
  echo "Built app not found. Run: npm run build:mac"
  exit 1
fi

export REGISTRY_URL="${REGISTRY_URL:-https://drive.google.com/uc?export=download&id=1_d6-xEbniM2MNqZu1JQtAxrUCsV8-rae}"
export REGISTRY_LICENSE_PUBLIC_KEY_HEX="${REGISTRY_LICENSE_PUBLIC_KEY_HEX:-5a838c50f67a4abbf6c1136f1acf1e8ee630b25c62fa87cd4c16953cb552a821}"

exec "$BIN"
