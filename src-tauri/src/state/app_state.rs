use serde::{Deserialize, Serialize};

use super::config_state::ConfigState;
use super::trading_state::TradingState;
use crate::license::validator::LicenseInfo;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppState {
    pub license: Option<LicenseInfo>,
    pub licensed: bool,
    pub trading: TradingState,
    pub config: ConfigState,
    /// config.json path we loaded at startup — save mirrors here so repo root file stays in sync.
    #[serde(skip, default)]
    pub config_loaded_from: Option<PathBuf>,
    pub sidecar_running: bool,
    pub connected_to_tws: bool,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            license: None,
            licensed: false,
            trading: TradingState::default(),
            config: ConfigState::default(),
            config_loaded_from: None,
            sidecar_running: false,
            connected_to_tws: false,
        }
    }
}
