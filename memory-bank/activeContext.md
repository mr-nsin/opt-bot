# Active Context: QuantDrift Options Trading Bot

## Current Focus of Work
* Completed and verified the senior performance engineering research master document at [performance_report.html](file:///Users/nitinsinghal/Documents/project/treetech/OPT_BOT/docs/performance_report.html) for August 3, 2026.
* Reviewed and documented all 25 performance techniques across application startup, memory usage, CPU usage, GPU acceleration, PyO3/Rust zero-copy interop, Shared Memory IPC, Numba JIT indicators, Polars SIMD pipelines, WebGPU rendering, QuestDB time-series streaming, and DuckDB 1.0 backtesting.
* Formulated latency guarantee matrices (< 1 ms, < 5 ms, < 10 ms), explicit Top 25 ROI ranking table, Top 10 quick wins, Top 10 architectural transformations, Top 10 experimental ideas, Top 10 libraries worth adopting, and Top 10 things NOT to do.

## Recent Decisions
* **Master Performance HTML Report:** Updated interactive dark-themed report at `docs/performance_report.html`.
* **Zero-Copy Architecture Standard:** Adopted Arrow PyCapsule interface (`pyo3-arrow`) and Shared Memory IPC (`mmap2`) as the standard for high-throughput Rust-Python communication.
* **Latency Guarantee Thresholds:** Established hard SLA targets (< 0.85 ms for order triggers, < 0.04 ms for PyO3 FFI data exchange, < 0.12 ms for Tauri IPC).

## Next Steps
* Begin implementing Phase 1 quick-wins (SQLite WAL mode tuning, Cargo release Fat LTO, Numba JIT indicators).
* Integrate Kaufman Adaptive ATR and EMA 21 parameter optimizations into `Indicators.py` and `BOT.py`.
* Prototype Shared Memory IPC bridge for Tauri v2 sidecar integration.


