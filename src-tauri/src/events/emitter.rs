use serde::Serialize;
use tauri::{AppHandle, Emitter};

/// Emit a typed event to the frontend
pub fn emit_event<T: Serialize + Clone>(handle: &AppHandle, event: &str, payload: &T) {
    if let Err(e) = handle.emit(event, payload) {
        log::error!("Failed to emit event '{}': {}", event, e);
    }
}

/// Standard event names used between Rust and React
pub mod events {
    // Trading events
    pub const TRADING_STARTED: &str = "trading:started";
    pub const TRADING_STOPPED: &str = "trading:stopped";
    pub const TRADING_ERROR: &str = "trading:error";

    // Market data events
    pub const TICK_UPDATE: &str = "trading:tick_update";
    pub const PNL_UPDATE: &str = "trading:pnl_update";
    pub const POSITION_UPDATE: &str = "trading:position_update";

    // Order events
    pub const ORDER_PLACED: &str = "trading:order_placed";
    pub const ORDER_FILLED: &str = "trading:order_filled";
    pub const ORDER_CANCELLED: &str = "trading:order_cancelled";

    // Signal events
    pub const SIGNAL_DETECTED: &str = "trading:signal_detected";
    pub const TRADE_EXECUTED: &str = "trading:trade_executed";
    pub const TRADE_CLOSED: &str = "trading:trade_closed";

    // System events
    pub const LOG_MESSAGE: &str = "trading:log_message";
    pub const CONNECTION_STATUS: &str = "trading:connection_status";
    pub const ENGINE_STATUS: &str = "trading:engine_status";

    // License events
    pub const LICENSE_VALIDATED: &str = "license:validated";
    pub const LICENSE_EXPIRED: &str = "license:expired";
}
