# How config.json Is Handled (Tauri Build vs Runtime)

## Short answer: **The Tauri build does NOT copy config.json**

- **Tauri build** (`npm run tauri:build` / `tauri build`): Does not bundle or copy `config.json`. Only the frontend (`dist`) and the external binary (`binaries/trading-engine-*`) are part of the bundle.
- **Trading-engine PyInstaller build** (`trading-engine/build.py`): Does not include `config.json`. It only bundles Python modules and `expiryStrike.json` (see `data_additions` in `build.py`).

So **config.json is never “recopied” by the build**. It is only read and written at **runtime**.

---

## Where config.json comes from at runtime

### 1. Tauri (Rust) app startup

- **Load:** `ConfigState::load_trading_config()` in `src-tauri/src/state/config_state.rs` tries, in order:
  1. **Project paths** from `project_config_paths()`:
     - `config.json` (relative to process CWD)
     - `{cwd}/config.json`
     - `{cwd}/../config.json`
  2. **App data** `{app_data_dir}/config.json`
  3. **Legacy** `./config.json`

So when you run the app from the project root (e.g. `npm run tauri:dev`), it typically loads **OPT_BOT/config.json** if that file exists.

### 2. When config.json is written (the “recopy” you see)

- **Rust** writes project `config.json` only when **saving** config:
  - The frontend calls the Tauri command **`save_config`** (e.g. when user saves in Settings or when the app persists config).
  - That calls `ConfigState::save_trading_config()`, which:
    1. Writes to **app data** `{app_data_dir}/config.json`.
    2. Then calls **`save_trading_config_to_project()`**, which writes the same config in **BOT.py key format** (IP, PORT, stockListToTrade, etc.) to:
       - The first path in `project_config_paths()` that **already exists**, or
       - If none exist, **`{cwd}/config.json`** (so it may create/overwrite the file next to the running app).

So the project’s **config.json is overwritten whenever the UI (or any caller) invokes `save_config`**, not when you run the Tauri build. The “recopy” is this runtime save.

### 3. Python sidecar (trading engine)

- When you click **Start Trading**, the Rust app sends the **current in-memory config** (from the UI / loaded at startup) to the sidecar.
- The **TradingEngine** (`trading-engine/engine/trading_engine.py`) in `_start_data_feed_and_strategies()`:
  - **If frozen (built binary):** Creates a **temp directory**, writes **config.json there** (from `self.config.to_bot_config_dict()`), and `chdir`s to that temp dir before importing BOT. It does **not** touch the project’s config.json.
  - **If not frozen (dev):** Uses **PARENT_DIR** (project root). It writes **config.json only if it does not already exist** (`if not os.path.isfile(config_path)`). So in dev it does **not** overwrite your project config.json when the file is already there.

---

## Summary

| Step | Copies / overwrites config.json? |
|------|----------------------------------|
| Tauri build | No. config.json is not part of the bundle. |
| Trading-engine PyInstaller build | No. Only code + expiryStrike.json are bundled. |
| App startup (Rust) | No. Only **loads** from project / app data / legacy paths. |
| **Save config from UI (Rust)** | **Yes.** Writes to app data and to **project config.json** (BOT format). |
| Start Trading – sidecar frozen | No. Writes only to a temp-dir config.json. |
| Start Trading – sidecar dev | Writes only if project config.json **does not exist**; does not overwrite existing. |

So the project **config.json** is overwritten when:
- Someone calls the Tauri **`save_config`** command (e.g. saving from the UI, or any code that triggers a config save).

If you want to avoid overwriting the project file, you could change `save_trading_config_to_project()` to only write to app data, or add a setting to disable writing to the project path.
