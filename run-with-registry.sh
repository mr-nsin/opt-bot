#!/usr/bin/env bash
# Run QuantDrift in dev mode with license registry env vars (macOS equivalent of run-with-registry.bat).
# Set your registry values here or export them before running.

export REGISTRY_URL="${REGISTRY_URL:-https://drive.google.com/uc?export=download&id=1_d6-xEbniM2MNqZu1JQtAxrUCsV8-rae}"
export REGISTRY_LICENSE_PUBLIC_KEY_HEX="${REGISTRY_LICENSE_PUBLIC_KEY_HEX:-5a838c50f67a4abbf6c1136f1acf1e8ee630b25c62fa87cd4c16953cb552a821}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

npm run tauri:dev
