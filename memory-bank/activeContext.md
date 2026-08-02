# Active Context: QuantDrift Options Trading Bot

## Current Focus of Work
* Generated a comprehensive performance engineering HTML report (`docs/performance_report.html`) covering sub-1ms/5ms/10ms latency optimization, PyO3 Arrow PyCapsule zero-copy interop, Shared Memory ring buffer IPC, Numba JIT compiled indicator kernels, Polars vectorized operations, WebGPU canvas rendering, QuestDB time-series streaming, and DuckDB analytical querying.
* Verified that all Memory Bank requirements and performance engineering tasks have been completed and synthesized.

## Recent Decisions
* **Performance Report HTML:** Built an interactive, dark-themed HTML report located at `docs/performance_report.html`.
* **Zero-Copy Architecture Standard:** Adopted Arrow PyCapsule interface (`pyo3-arrow`) and Shared Memory IPC (`mmap2`) as the standard for high-throughput Rust-Python communication.

## Next Steps
* Begin implementing Phase 1 quick-wins (SQLite WAL mode tuning, Cargo release Fat LTO, Numba JIT indicators).
* Prototype Shared Memory IPC bridge for Tauri v2 sidecar integration.
* Backtest 0DTE Differential Machine Learning SVJD model.
