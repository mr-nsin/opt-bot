# Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 4b. Bug Fix Workflow (see `.cursor/rules/fix-and-test.mdc`)
- **Create a test** for every fix — test fails before, passes after
- **Run tests first** — never mark done until tests pass
- **Verify no regressions** — run broader suite; check related functionality

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
- **Test Everything**: Verify changes work before marking done. Check logs, run tests.
- **Own the Fix**: When something breaks, fix it end-to-end. Don't leave partial solutions.

## Antigravity skill library (default reference for this repo)

Installed skills live on disk (not in the model by default). **On every substantive prompt** (anything beyond a one-line answer), map the task to the tables below and **read the matching `SKILL.md` file(s)** with the editor’s Read tool **before** designing, refactoring, or adding features. Treat that content as project guidance for this session’s work.

**Base path (expand `~` to the user home directory on macOS):**

`~/.gemini/antigravity/skills/<skill-name>/SKILL.md`

**Rules**

- **Selective loading:** Read **1–4** skill files per task that clearly apply. Do **not** read the entire skills directory or unrelated skills.
- **Stack match first:** Prefer stack skills for implementation; pull **architecture** skills when boundaries, ADRs, APIs, or structure are in scope.
- **Honest limit:** No process can inject all skill text into a single context window; **curated reads** are how we keep quality without blowing the budget.
- **Scripts:** Some skills (e.g. `senior-architect`) mention helper scripts. **Inspect before run**; do not execute untrusted automation on production paths.

### Stack-aligned skills (React / TypeScript / Tailwind / Zustand / Rust / Python / quant)

| Skill folder | Use when |
|--------------|----------|
| `typescript-pro` | TS types, strictness, shared shapes with RPC/config |
| `react-best-practices` | Components, hooks, composition, React quality |
| `zustand-store-ts` | Global/client state (`src/stores/`, Zustand) |
| `tailwind-patterns` | Tailwind layout, tokens, UI consistency |
| `rust-pro` | Tauri Rust: commands, state, sidecar lifecycle |
| `rust-async-patterns` | Async Rust, concurrency at the shell boundary |
| `python-pro` | Trading engine and root Python modules |
| `async-python-patterns` | Async I/O, long-running engine loops |
| `python-testing-patterns` | `pytest`, engine tests, regression safety |
| `quant-analyst` | Options/quant framing, risk/time-series language (not IBKR-specific) |

### Architect- and system-level skills

| Skill folder | Use when |
|--------------|----------|
| `architecture` | Trade-offs, requirements, decision framework, ADR mindset |
| `software-architecture` | Clean architecture, DDD-style boundaries, layering FE vs domain vs infra |
| `api-design-principles` | Contracts between UI, Tauri, and Python; errors, versioning, clarity |
| `backend-architect` | Service/API design, resilience, observability behind the engine |
| `monorepo-architect` | Repo-wide packages, builds, CI, shared boundaries (this repo is multi-stack) |
| `architecture-decision-records` | Writing or updating ADRs for major decisions |
| `architecture-patterns` | Choosing structural patterns |
| `architect-review` | Structured review of proposed designs |
| `c4-architecture-c4-architecture` | C4-style documentation of context/containers/components |
| `full-stack-orchestration-full-stack-feature` | End-to-end feature flow: data → API → UI → integration (use as checklist; subagent names inside may be tool-specific) |

**Optional:** `antigravity-skill-orchestrator` when unsure which single skill fits; `senior-architect` only if you need its scripted workflows after review.

### Cursor-bundled skills (separate path)

Cursor may also expose skills under `~/.cursor/skills-cursor/` (e.g. create-rule, create-skill). Use those when the task is editor rules, skills authoring, or settings — not for trading logic.

## Project Context: QuantDrift OPT_BOT

This is a **Tauri + React + Python** desktop trading application for options trading via Interactive Brokers (IBKR).

### Architecture
- **Frontend**: React + TypeScript + Tailwind CSS (Vite dev server on port 1420)
- **Backend**: Rust (Tauri) manages window, licensing, sidecar lifecycle
- **Trading Engine**: Python sidecar (`trading-engine/`) communicates via JSON-RPC over stdio
- **Legacy Python**: `BOT.py`, `common.py`, `order_manager.py`, `tws_api_client.py`, `Indicators.py` at project root
- **Account scope** (`account_scope.py` + `tws_api_client.managed_account_ids`): **Display** vs **execution** boundary for IBKR. Empty `ACCOUNT_ID` → show all option legs TWS reports; set → filter Positions tab and set `order.account` in BOT. If configured id is **not** in TWS `managedAccounts`, position filtering **fails open** (show all) with a WARN so a typo does not blank the Active Positions tab — **orders may still use the bad id** until the user fixes config.

### Key Paths
| Path | Purpose |
|------|---------|
| `src/` | React frontend components, hooks, stores |
| `src-tauri/` | Rust backend (Tauri commands, sidecar manager, licensing) |
| `trading-engine/` | Python trading engine sidecar (entry: `main.py`) |
| `trading-engine/.venv/` | Python 3.12 virtualenv (all engine deps) |
| `config.json` | Trading config (IP, port, symbols, risk params) |
| `config/settings.json` | UI settings |
| `docs/` | **ARCHITECTURE.md** (C4-style, protocol contract), ROADMAP.md, `architecture/adr/` |
| `logs/trade_open_context.jsonl` | Entry-order audit: full signal OHLCV + SuperTrend DF + engulf window, algo bars, execution (queued async — see `trade_placement_audit.py`) |

### Running the App (macOS)
**Dev mode:**
```bash
./run-with-registry.sh
# or manually:
export REGISTRY_URL="https://drive.google.com/uc?export=download&id=1_d6-xEbniM2MNqZu1JQtAxrUCsV8-rae"
export REGISTRY_LICENSE_PUBLIC_KEY_HEX="5a838c50f67a4abbf6c1136f1acf1e8ee630b25c62fa87cd4c16953cb552a821"
npm run tauri:dev
```
**Build runnable .app (equivalent to exe on Windows):**
```bash
npm run build:mac                    # Apple Silicon only
npm run build:mac:universal         # Intel + Apple Silicon (universal)
# Output: src-tauri/target/release/bundle/macos/QuantDrift.app
open src-tauri/target/release/bundle/macos/QuantDrift.app
# Or run with registry env vars:
./run-built-mac.sh
```
If port 1420 is in use: `lsof -ti:1420 | xargs kill -9`

### Python Environment
- The trading engine runs inside `trading-engine/.venv/` (Python 3.12)
- The sidecar wrapper at `src-tauri/binaries/trading-engine-aarch64-apple-darwin` auto-detects this venv
- System Python is 3.14 (incompatible with pandas_ta) — always use the venv
- Install deps: `cd trading-engine && .venv/bin/pip install -r requirements.txt`

### Common Issues & Fixes
| Issue | Fix |
|-------|-----|
| Port 1420 in use | `lsof -ti:1420 \| xargs kill -9` |
| `ModuleNotFoundError: loguru` | Recreate venv with Python 3.12, install requirements |
| `pandas._config` error | Don't use Python 3.14; use 3.12 venv |
| Tailwind opacity `/8` error | Use `/10` instead (Tailwind doesn't support `/8`) |
| `tauri build --ci` invalid value | Use `tauri build --ci false` |
| No trading signals | Check TWS connection (error 10197/162), verify data feed prices aren't -1 |

### Git
- Branch: `opt-bot` (tracking `origin/opt-bot`)
- Remote: `https://github.com/mr-nsin/opt-bot.git`
- Don't commit: `expiryStrike.json`, `license.json`, `db/`, `.venv/`, `logs/`
