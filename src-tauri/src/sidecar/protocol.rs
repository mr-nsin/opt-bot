use serde::{Deserialize, Serialize};

/// Request message sent from Rust to Python sidecar
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SidecarRequest {
    pub id: String,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,
}

/// Response message from Python sidecar to Rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SidecarResponse {
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<SidecarError>,
}

/// Error in sidecar response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SidecarError {
    pub code: i32,
    pub message: String,
}

/// Event message from Python sidecar (unsolicited)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SidecarEvent {
    pub event: String,
    pub data: serde_json::Value,
}

/// Union type for any message from the sidecar
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum SidecarMessage {
    Response(SidecarResponse),
    Event(SidecarEvent),
}

/// Known event types from the Python sidecar
pub mod event_types {
    pub const TICK_UPDATE: &str = "tick_update";
    pub const POSITION_UPDATE: &str = "position_update";
    pub const ORDER_UPDATE: &str = "order_update";
    pub const PNL_UPDATE: &str = "pnl_update";
    pub const SIGNAL_DETECTED: &str = "signal_detected";
    pub const TRADE_EXECUTED: &str = "trade_executed";
    pub const TRADE_CLOSED: &str = "trade_closed";
    pub const LOG_MESSAGE: &str = "log_message";
    pub const ERROR: &str = "error";
    pub const ENGINE_STATUS: &str = "engine_status";
    pub const CONNECTION_STATUS: &str = "connection_status";
}

/// Known method names for requests to the sidecar
pub mod methods {
    pub const START_TRADING: &str = "start_trading";
    pub const STOP_TRADING: &str = "stop_trading";
    pub const EMERGENCY_STOP: &str = "emergency_stop";
    pub const GET_STATUS: &str = "get_status";
    pub const GET_POSITIONS: &str = "get_positions";
    pub const CLOSE_POSITION: &str = "close_position";
    pub const CLOSE_ALL: &str = "close_all";
    pub const CLOSE_ALL_CALLS: &str = "close_all_calls";
    pub const CLOSE_ALL_PUTS: &str = "close_all_puts";
    pub const UPDATE_CONFIG: &str = "update_config";
    pub const PING: &str = "ping";
    pub const SIMULATE_DEMO: &str = "simulate_demo";
}

impl SidecarRequest {
    pub fn new(method: &str, params: Option<serde_json::Value>) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            method: method.to_string(),
            params,
        }
    }
}
