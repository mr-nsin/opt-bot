use std::path::PathBuf;

/// Get the application data directory
pub fn app_data_dir() -> PathBuf {
    directories::ProjectDirs::from("com", "quantdrift", "optbot")
        .map(|dirs| dirs.data_dir().to_path_buf())
        .unwrap_or_else(|| PathBuf::from("."))
}

/// Get the application config directory
pub fn app_config_dir() -> PathBuf {
    directories::ProjectDirs::from("com", "quantdrift", "optbot")
        .map(|dirs| dirs.config_dir().to_path_buf())
        .unwrap_or_else(|| PathBuf::from("."))
}

/// Get the logs directory
pub fn logs_dir() -> PathBuf {
    let mut path = app_data_dir();
    path.push("logs");
    if !path.exists() {
        std::fs::create_dir_all(&path).ok();
    }
    path
}

/// Get the database directory
pub fn db_dir() -> PathBuf {
    let mut path = app_data_dir();
    path.push("db");
    if !path.exists() {
        std::fs::create_dir_all(&path).ok();
    }
    path
}
