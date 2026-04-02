use std::collections::{HashMap, HashSet};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Arc;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tokio::sync::{Mutex, oneshot};

/// Recently-closed position keys with timestamps.
/// Prevents position_update from re-adding positions that trade_closed just removed.
static RECENTLY_CLOSED: once_cell::sync::Lazy<
    Arc<Mutex<HashMap<String, std::time::Instant>>>,
> = once_cell::sync::Lazy::new(|| Arc::new(Mutex::new(HashMap::new())));

const RECENTLY_CLOSED_TTL: std::time::Duration = std::time::Duration::from_secs(10);

use super::protocol::{SidecarMessage, SidecarRequest};
use crate::commands::logs::{push_log, LogEntry};
use crate::state::app_state::AppState;
use crate::state::trading_state::{Position, TradeRecord, TradingStatus};

/// Embedded trading-engine binary (built by prebuild before Tauri compile).
/// Enables single-exe distribution: extract and run when sidecar not found.
#[cfg(all(target_os = "windows", target_arch = "x86_64"))]
const EMBEDDED_ENGINE: &[u8] = include_bytes!("../../binaries/trading-engine-x86_64-pc-windows-msvc.exe");

#[cfg(not(all(target_os = "windows", target_arch = "x86_64")))]
const EMBEDDED_ENGINE: &[u8] = &[];

/// Global sidecar child process handle
static SIDECAR_CHILD: once_cell::sync::Lazy<
    Arc<Mutex<Option<tauri_plugin_shell::process::CommandChild>>>,
> = once_cell::sync::Lazy::new(|| Arc::new(Mutex::new(None)));

/// Track the sidecar PID so we can force-kill the process tree on Windows
static SIDECAR_PID: once_cell::sync::Lazy<Arc<Mutex<Option<u32>>>> =
    once_cell::sync::Lazy::new(|| Arc::new(Mutex::new(None)));

/// When true, we explicitly killed the sidecar (emergency_stop/stop_trading) — do not log "terminated"
static EXPECTED_TERMINATION: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(false);

/// Assign the trading-engine child to a Windows Job Object with kill-on-close.
/// When the main process exits (X button, Task Manager, crash), the OS closes
/// all job handles and automatically terminates the child.
/// Only the trading-engine is in the job — WebView2 is unaffected.
#[cfg(windows)]
fn attach_child_to_kill_job(pid: u32) {
    use windows_sys::Win32::System::Threading::{OpenProcess, PROCESS_ALL_ACCESS};

    let handle = unsafe { OpenProcess(PROCESS_ALL_ACCESS, 0, pid) };
    if handle.is_null() {
        log::warn!("OpenProcess({pid}) returned null handle");
        return;
    }

    match win32job::Job::create() {
        Ok(job) => {
            match job.query_extended_limit_info() {
                Ok(mut info) => {
                    info.limit_kill_on_job_close();
                    if let Err(e) = job.set_extended_limit_info(&mut info) {
                        log::warn!("Job set limits failed: {e}");
                        return;
                    }
                }
                Err(e) => {
                    log::warn!("Job query limits failed: {e}");
                    return;
                }
            }
            if let Err(e) = job.assign_process(handle as isize) {
                log::warn!("Job assign_process({pid}) failed: {e}");
                return;
            }
            std::mem::forget(job);
            log::info!("Trading-engine (pid {pid}) attached to kill-on-close job object");
        }
        Err(e) => log::warn!("Job create failed: {e}"),
    }
}

/// Initialize the sidecar manager (called at app startup)
pub async fn init(_handle: &AppHandle) -> Result<(), String> {
    log::info!("Sidecar manager initialized");
    Ok(())
}

/// Extract embedded trading-engine to temp file and return path.
fn extract_embedded_engine() -> Result<PathBuf, String> {
    if EMBEDDED_ENGINE.is_empty() {
        return Err("Embedded trading engine not available for this platform".into());
    }
    let temp_dir = std::env::temp_dir().join("quantdrift");
    std::fs::create_dir_all(&temp_dir).map_err(|e| format!("Create temp dir: {}", e))?;
    let exe_path = temp_dir.join("trading-engine.exe");
    let mut f = std::fs::File::create(&exe_path).map_err(|e| format!("Create temp exe: {}", e))?;
    f.write_all(EMBEDDED_ENGINE).map_err(|e| format!("Write temp exe: {}", e))?;
    f.sync_all().map_err(|e| format!("Sync temp exe: {}", e))?;
    drop(f);
    log::info!("Extracted embedded trading-engine to {:?}", exe_path);
    Ok(exe_path)
}

/// Spawn the Python trading engine sidecar.
/// Tries Tauri sidecar first (when binaries/ exists); falls back to embedded exe for single-file distribution.
pub async fn spawn_sidecar(handle: &AppHandle) -> Result<(), String> {
    let mut child_lock = SIDECAR_CHILD.lock().await;

    if child_lock.is_some() {
        return Err("Sidecar is already running".into());
    }

    let shell = handle.shell();

    // Try sidecar first (when running from build or installed bundle)
    let (mut rx, child) = match shell.sidecar("trading-engine") {
        Ok(cmd) => match cmd.spawn() {
            Ok((rx, child)) => (rx, child),
            Err(e) => {
                let msg = e.to_string();
                // Fallback to embedded when sidecar binary not found
                #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
                if msg.contains("not compatible") || msg.contains("os error 216") || msg.contains("not found") || msg.contains("The system cannot find") {
                    let exe_path = extract_embedded_engine()?;
                    let (rx, child) = shell
                        .command(exe_path.to_string_lossy().as_ref())
                        .spawn()
                        .map_err(|e2| format!("Failed to spawn embedded trading engine: {}", e2))?;
                    (rx, child)
                } else {
                    return Err(format!("Failed to spawn trading engine: {}", msg));
                }
                #[cfg(not(all(target_os = "windows", target_arch = "x86_64")))]
                return Err(format!("Failed to spawn trading engine: {}", msg));
            }
        },
        Err(e) => {
            #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
            {
                log::warn!("Sidecar not found ({}), trying embedded engine", e);
                let exe_path = extract_embedded_engine()?;
                let (rx, child) = shell
                    .command(exe_path.to_string_lossy().as_ref())
                    .spawn()
                    .map_err(|e2| format!("Failed to spawn embedded trading engine: {}", e2))?;
                (rx, child)
            }
            #[cfg(not(all(target_os = "windows", target_arch = "x86_64")))]
            return Err(format!("Trading engine not found: {}. Build with: cd trading-engine && python build.py", e));
        }
    };

    let pid = child.pid();

    // Attach to a Windows Job Object so the child is auto-killed if the main process dies
    #[cfg(windows)]
    attach_child_to_kill_job(pid);

    *child_lock = Some(child);
    drop(child_lock);

    // Store PID for force-kill fallback
    *SIDECAR_PID.lock().await = Some(pid);

    // Spawn event listener task
    let app_handle = handle.clone();
    tauri::async_runtime::spawn(async move {
        use tauri_plugin_shell::process::CommandEvent;

        // Get AppState from the managed state so we can update it from sidecar events
        let app_state: Arc<Mutex<AppState>> =
            app_handle.state::<Arc<Mutex<AppState>>>().inner().clone();

        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    if let Ok(msg) = serde_json::from_str::<SidecarMessage>(&line_str) {
                        handle_sidecar_message(&app_handle, msg, &app_state).await;
                    } else {
                        log::debug!("Sidecar stdout (non-JSON): {}", line_str);
                    }
                }
                CommandEvent::Stderr(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    log::warn!("Sidecar stderr: {}", line_str);
                    let _ = app_handle.emit("sidecar-error", &line_str);

                    // Also push stderr lines to the log buffer
                    push_log(LogEntry {
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        level: "WARN".into(),
                        category: "sidecar".into(),
                        message: line_str.to_string(),
                    })
                    .await;
                }
                CommandEvent::Error(err) => {
                    log::error!("Sidecar error: {}", err);
                    let _ = app_handle.emit("sidecar-error", &err);
                }
                CommandEvent::Terminated(payload) => {
                    log::info!("Sidecar terminated with code: {:?}", payload.code);
                    let _ = app_handle.emit("sidecar-terminated", &payload.code);

                    // Update app state when sidecar dies
                    {
                        let mut app = app_state.lock().await;
                        app.sidecar_running = false;
                        app.trading.status = TradingStatus::Idle;
                        app.connected_to_tws = false;
                    }

                    // Only log "terminated" when it was unexpected (crash); skip when we killed it
                    if !EXPECTED_TERMINATION.swap(false, std::sync::atomic::Ordering::SeqCst) {
                        push_log(LogEntry {
                            timestamp: chrono::Utc::now().to_rfc3339(),
                            level: "WARN".into(),
                            category: "system".into(),
                            message: format!(
                                "Trading engine process terminated (code: {:?})",
                                payload.code
                            ),
                        })
                        .await;
                    }

                    // Clean up child handle and PID
                    let mut child_lock = SIDECAR_CHILD.lock().await;
                    *child_lock = None;
                    drop(child_lock);
                    *SIDECAR_PID.lock().await = None;
                }
                _ => {}
            }
        }
    });

    log::info!("Python sidecar spawned successfully");
    Ok(())
}

/// Send a request to the sidecar
pub async fn send_request(request: &SidecarRequest) -> Result<(), String> {
    let mut child_lock = SIDECAR_CHILD.lock().await;

    if let Some(child) = child_lock.as_mut() {
        let json = serde_json::to_string(request).map_err(|e| format!("Serialize: {}", e))?;
        let msg = format!("{}\n", json);
        child
            .write(msg.as_bytes())
            .map_err(|e| format!("Write to sidecar: {}", e))?;
        Ok(())
    } else {
        Err("Sidecar is not running".into())
    }
}

/// Mark that we are about to kill the sidecar so "terminated" log is suppressed
pub fn set_expected_termination(expected: bool) {
    EXPECTED_TERMINATION.store(expected, std::sync::atomic::Ordering::SeqCst);
}

/// Kill the sidecar process and its entire process tree
pub async fn kill_sidecar() -> Result<(), String> {
    let pid = SIDECAR_PID.lock().await.take();

    let mut child_lock = SIDECAR_CHILD.lock().await;
    if let Some(child) = child_lock.take() {
        let _ = child.kill();
        log::info!("Sidecar child.kill() called");
    }
    drop(child_lock);

    // On Windows, also use taskkill /F /T to kill the entire process tree.
    // PyInstaller --onefile spawns a child process that child.kill() may not reach.
    #[cfg(windows)]
    if let Some(p) = pid {
        log::info!("Force-killing sidecar process tree (pid {p}) via taskkill");
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/T", "/PID", &p.to_string()])
            .creation_flags(CREATE_NO_WINDOW)
            .output();
    }

    Ok(())
}

/// Check if sidecar is running
pub async fn is_running() -> bool {
    SIDECAR_CHILD.lock().await.is_some()
}

/// Pending request-response: request_id -> oneshot sender for result
static PENDING_REQUESTS: once_cell::sync::Lazy<std::sync::Mutex<HashMap<String, oneshot::Sender<Result<serde_json::Value, String>>>>> =
    once_cell::sync::Lazy::new(|| std::sync::Mutex::new(HashMap::new()));

/// Send request to sidecar and wait for response (with 5s timeout).
/// Returns the result from the sidecar, or error if timeout/sidecar not running.
pub async fn send_request_and_wait(request: &SidecarRequest) -> Result<serde_json::Value, String> {
    let (tx, rx) = oneshot::channel();
    {
        let mut pending = PENDING_REQUESTS.lock().map_err(|e| e.to_string())?;
        pending.insert(request.id.clone(), tx);
    }

    send_request(request).await?;

    tokio::time::timeout(std::time::Duration::from_secs(5), rx)
        .await
        .map_err(|_| "Timeout waiting for sidecar response".to_string())?
        .map_err(|_| "Sidecar response channel closed".to_string())?
}

/// Handle incoming messages from the sidecar.
/// Updates the Rust AppState and forwards events to the React frontend.
async fn handle_sidecar_message(
    handle: &AppHandle,
    msg: SidecarMessage,
    state: &Arc<Mutex<AppState>>,
) {
    match msg {
        SidecarMessage::Event(event) => {
            // Skip forwarding to frontend when payload is unchanged (P3 optimization)
            let mut should_forward = true;

            // ---- Update Rust-side AppState based on event type ----
            match event.event.as_str() {
                "pnl_update" => {
                    let daily = event
                        .data
                        .get("daily_pnl")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);
                    let unrealized = event
                        .data
                        .get("unrealized_pnl")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);
                    let realized = event
                        .data
                        .get("realized_pnl")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);

                    let mut app = state.lock().await;
                    app.trading.daily_pnl.total = daily;
                    app.trading.daily_pnl.unrealized = unrealized;
                    app.trading.daily_pnl.realized = realized;
                }

                "position_update" => {
                    if let Ok(pos) = serde_json::from_value::<Position>(event.data.clone()) {
                        let norm_exp = |e: &str| e.replace('-', "").replace(' ', "").trim().to_string();
                        let norm_right = |r: &str| -> String {
                            let u = r.to_uppercase();
                            if u.starts_with('C') {
                                "C".to_string()
                            } else if u.starts_with('P') {
                                "P".to_string()
                            } else {
                                r.to_string()
                            }
                        };

                        // Guard: skip updates for recently-closed positions to prevent ghost re-adds
                        let rc_key = format!(
                            "{}-{}-{}-{}",
                            pos.symbol,
                            format!("{:.0}", pos.strike),
                            norm_right(&pos.right),
                            norm_exp(&pos.expiry)
                        );
                        let is_recently_closed = {
                            let rc = RECENTLY_CLOSED.lock().await;
                            rc.get(&rc_key).map_or(false, |ts| ts.elapsed() < RECENTLY_CLOSED_TTL)
                        };
                        if is_recently_closed {
                            log::debug!("Skipping position_update for recently-closed: {}", rc_key);
                            should_forward = false;
                        } else {
                            let mut app = state.lock().await;
                            if let Some(existing) = app
                                .trading
                                .positions
                                .iter_mut()
                                .find(|p| {
                                    p.symbol == pos.symbol
                                        && (p.strike - pos.strike).abs() < 0.01
                                        && norm_right(&p.right) == norm_right(&pos.right)
                                        && norm_exp(&p.expiry) == norm_exp(&pos.expiry)
                                })
                            {
                                *existing = pos;
                            } else {
                                app.trading.positions.push(pos);
                            }
                        }
                    }
                }

                "positions_snapshot" => {
                    // Batch position update: replace all positions at once (1 IPC call)
                    // Recently-closed positions are filtered out to prevent ghost re-adds
                    if let Some(arr) = event.data.get("positions").and_then(|v| v.as_array()) {
                        let rc = RECENTLY_CLOSED.lock().await;
                        let norm_exp_fn = |e: &str| e.replace('-', "").replace(' ', "").trim().to_string();
                        let norm_right_fn = |r: &str| -> String {
                            let u = r.to_uppercase();
                            if u.starts_with('C') { "C".to_string() }
                            else if u.starts_with('P') { "P".to_string() }
                            else { r.to_string() }
                        };
                        let mut new_positions = Vec::new();
                        for item in arr {
                            if let Ok(pos) = serde_json::from_value::<Position>(item.clone()) {
                                let rc_key = format!(
                                    "{}-{}-{}-{}",
                                    pos.symbol,
                                    format!("{:.0}", pos.strike),
                                    norm_right_fn(&pos.right),
                                    norm_exp_fn(&pos.expiry)
                                );
                                if rc.get(&rc_key).map_or(false, |ts| ts.elapsed() < RECENTLY_CLOSED_TTL) {
                                    continue; // skip recently-closed
                                }
                                new_positions.push(pos);
                            }
                        }
                        drop(rc);
                        let mut app = state.lock().await;
                        app.trading.positions = new_positions;
                    }
                }

                "trade_executed" => {
                    if let Ok(trade) = serde_json::from_value::<TradeRecord>(event.data.clone()) {
                        let mut app = state.lock().await;
                        app.trading.total_trades += 1;
                        app.trading.trades_today.push(trade);
                    } else {
                        // Even if we can't fully deserialize, count the trade
                        let mut app = state.lock().await;
                        app.trading.total_trades += 1;
                    }
                }

                "trade_closed" => {
                    let pnl = event.data.get("pnl").and_then(|v| v.as_f64());
                    let exit_price = event.data.get("exit_price").and_then(|v| v.as_f64());
                    let closed_symbol = event.data.get("symbol").and_then(|v| v.as_str()).unwrap_or("");
                    let closed_strike = event.data.get("strike").and_then(|v| v.as_f64());
                    let closed_right = event.data.get("right").and_then(|v| v.as_str()).unwrap_or("");
                    let closed_expiry = event.data
                        .get("expiry")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .replace('-', "")
                        .trim()
                        .to_string();

                    let mut app = state.lock().await;

                    if let Some(pnl_val) = pnl {
                        if pnl_val > 0.0 {
                            app.trading.winning_trades += 1;
                        } else if pnl_val < 0.0 {
                            app.trading.losing_trades += 1;
                        }
                        // pnl == 0: break-even, don't count as win or loss
                    }

                    // Update matching open trade in trades_today with pnl so hydration returns complete data
                    fn norm_right(r: &str) -> String {
                        if r.eq_ignore_ascii_case("call") {
                            "C".to_string()
                        } else if r.eq_ignore_ascii_case("put") {
                            "P".to_string()
                        } else {
                            r.to_string()
                        }
                    }
                    for t in app.trading.trades_today.iter_mut() {
                        let is_open = t.status == "open" || t.status.is_empty();
                        if !is_open {
                            continue;
                        }
                        let symbol_ok = closed_symbol.is_empty() || t.symbol == closed_symbol;
                        let strike_ok = closed_strike.map_or(true, |s| (t.strike - s).abs() < 0.01);
                        let right_ok = closed_right.is_empty()
                            || norm_right(&t.right) == norm_right(closed_right)
                            || t.right == closed_right;
                        let expiry_ok = closed_expiry.is_empty()
                            || t.expiry.replace('-', "").trim() == closed_expiry;
                        if symbol_ok && strike_ok && right_ok && expiry_ok {
                            t.status = "closed".to_string();
                            t.exit_price = exit_price;
                            t.pnl = pnl;
                            break;
                        }
                    }

                    // Remove matching position (by symbol + strike + right for options)
                    if !closed_symbol.is_empty() {
                        app.trading.positions.retain(|p| {
                            if p.symbol != closed_symbol {
                                return true;
                            }
                            if let Some(s) = closed_strike {
                                if (p.strike - s).abs() > 0.01 {
                                    return true;
                                }
                            }
                            if !closed_right.is_empty() && p.right != closed_right {
                                return true;
                            }
                            false
                        });

                        // Add to recently-closed guard so position_update doesn't re-add this position
                        let rc_key = format!(
                            "{}-{}-{}-{}",
                            closed_symbol,
                            closed_strike.map_or("0".to_string(), |s| format!("{:.0}", s)),
                            norm_right(closed_right),
                            closed_expiry
                        );
                        let mut rc = RECENTLY_CLOSED.lock().await;
                        rc.insert(rc_key, std::time::Instant::now());
                        // Prune expired entries
                        rc.retain(|_, ts| ts.elapsed() < RECENTLY_CLOSED_TTL);
                    }
                }

                "connection_status" => {
                    if let Some(connected) =
                        event.data.get("connected").and_then(|v| v.as_bool())
                    {
                        let mut app = state.lock().await;
                        app.connected_to_tws = connected;
                    }
                }

                "signal_detected" => {
                    let signal_str = serde_json::to_string(&event.data).unwrap_or_default();
                    let mut app = state.lock().await;
                    app.trading.last_signal = Some(signal_str);
                    app.trading.last_signal_time =
                        Some(chrono::Utc::now().to_rfc3339());
                }

                "signal_data" => {
                    let mut app = state.lock().await;
                    app.trading.signal_data = Some(event.data.clone());
                }

                "account_metrics" => {
                    should_forward = false; // We emit explicitly; avoid double emit from generic forward
                    let mut app = state.lock().await;
                    let unchanged = app
                        .trading
                        .account_metrics
                        .as_ref()
                        .map(|prev| prev == &event.data)
                        .unwrap_or(false);
                    app.trading.account_metrics = Some(event.data.clone());
                    drop(app);
                    if !unchanged {
                        if let Err(e) = handle.emit("trading:account_metrics", &event.data) {
                            log::error!("Failed to emit account_metrics: {}", e);
                        }
                    }
                }

                "engine_status" => {
                    if let Some(status_str) =
                        event.data.get("status").and_then(|v| v.as_str())
                    {
                        let mut app = state.lock().await;
                        match status_str {
                            "Running" => app.trading.status = TradingStatus::Running,
                            "Idle" => app.trading.status = TradingStatus::Idle,
                            "Starting" => app.trading.status = TradingStatus::Starting,
                            "Stopping" => app.trading.status = TradingStatus::Stopping,
                            _ => {}
                        }
                        if let Some(connected) =
                            event.data.get("connected").and_then(|v| v.as_bool())
                        {
                            app.connected_to_tws = connected;
                        }
                    }
                }

                "log_message" => {
                    // Push sidecar log messages into the Rust in-memory log buffer.
                    // Supports both batched (entries array) and single-entry format.
                    let entries: Vec<LogEntry> = if let Some(arr) = event.data.get("entries").and_then(|v| v.as_array()) {
                        arr.iter()
                            .filter_map(|e| {
                                let timestamp = e.get("timestamp").and_then(|v| v.as_str()).unwrap_or("").to_string();
                                let level = e.get("level").and_then(|v| v.as_str()).unwrap_or("INFO").to_string();
                                let category = e.get("category").and_then(|v| v.as_str()).unwrap_or("trading").to_string();
                                let message = e.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string();
                                Some(LogEntry { timestamp, level, category, message })
                            })
                            .collect()
                    } else {
                        let timestamp = event
                            .data
                            .get("timestamp")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();
                        let level = event
                            .data
                            .get("level")
                            .and_then(|v| v.as_str())
                            .unwrap_or("INFO")
                            .to_string();
                        let category = event
                            .data
                            .get("category")
                            .and_then(|v| v.as_str())
                            .unwrap_or("trading")
                            .to_string();
                        let message = event
                            .data
                            .get("message")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();
                        vec![LogEntry { timestamp, level, category, message }]
                    };
                    for entry in entries {
                        push_log(entry).await;
                    }
                }

                _ => {}
            }

            // ---- Forward events to the React frontend (skip when redundant per P3) ----
            if should_forward {
                let event_name = format!("trading:{}", event.event);
                if let Err(e) = handle.emit(&event_name, &event.data) {
                    log::error!("Failed to emit event {}: {}", event_name, e);
                }
            }
        }

        SidecarMessage::Response(response) => {
            // Complete any pending request waiting for this response
            if let Ok(mut pending) = PENDING_REQUESTS.lock() {
                if let Some(tx) = pending.remove(&response.id) {
                    let result = match &response.error {
                        Some(err) => Err(err.message.clone()),
                        None => Ok(response.result.clone().unwrap_or(serde_json::Value::Array(vec![]))),
                    };
                    let _ = tx.send(result);
                }
            }
            // Forward responses with a consistent event name
            if let Err(e) = handle.emit("sidecar:response", &response) {
                log::error!("Failed to emit response: {}", e);
            }
        }
    }
}
