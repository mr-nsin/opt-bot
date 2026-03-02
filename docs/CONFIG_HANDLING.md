# How config.json Is Handled (Tauri Build vs Runtime)

## Standalone exe: no resources folder needed

config.json is **embedded in the binary** at compile time via `include_str!`. The exe can run as a single file (plus the trading-engine binary) without a separate resources folder.

**Load order** (first found wins):

1. **Resource dir** `{resource_dir}/config.json` — only if you bundle resources
2. **Project paths** — `config.json` next to exe, `{cwd}/config.json`, etc.
3. **App data** `{app_data_dir}/config.json` — from prior saves
4. **Legacy** `./config.json`
5. **Embedded** — config.json compiled into the exe (standalone fallback)

---

## Why resources folder existed (now optional)

Previously, config.json was in `bundle.resources` so the exe could load it from disk. That required a `resources/` folder next to the exe. For a standalone exe (single file), that was a problem: copying just the exe would miss config.json.

**Fix:** config.json is now embedded in the binary. The exe reads from:
- Filesystem paths first (config next to exe, app data, etc.)
- Falls back to embedded config when no file is found

No resources folder is needed. Run the exe alone; it uses the config that was in the project root at build time.

---

## Build requirement

Ensure `config.json` exists at the project root with your symbols (SPY, QQQ, TSLA, etc.) **before** `npm run tauri:build`. That file is embedded into the exe at build time.

---

## Default symbols

When config has no symbols, defaults are **all symbols** from config.json (SPY, QQQ, TSLA, AMZN, AAPL, AMD, NVDA, MSFT, BABA), not MNQU5/NQU5.

---

## Save from UI

Writes to app data + project `config.json` when paths exist.
