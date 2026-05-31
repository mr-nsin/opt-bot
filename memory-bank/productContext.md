# Product Context: QuantDrift Options Trading Bot

## Why This Product Exists
Options trading is highly time-sensitive. Traders need a tool that can monitor charts, parse technical setups, select contracts using strike/delta algorithms, and transmit orders to the broker in milliseconds.

QuantDrift bridges the gap between complex algorithmic options models and visual ease of use. It shields traders from the tedious process of manual calculation (e.g., tracking ATR pullbacks, manual delta-based strike selections) by automating execution directly through Interactive Brokers (IB).

## Target Users & Pain Points
* **Retail Options Day Traders:** Unable to monitor multiple charts concurrently for breakout signals or manage the extreme volatility of 0DTE options.
* **Algorithmic Traders:** Want to deploy technical strategies (like SuperTrend) without writing a bespoke order routing and UI dashboard interface from scratch.
* **Risk-Averse Investors:** Prone to emotional mistakes, needing strict drawdown limits, daily profit targets, and automated trailing stops enforced precisely at the API layer.

## How it Works (Detailed Workflow)
1. **Selection & Connection:** Users select the target symbols in the watchlist and toggle between **Demo** (paper trading) and **Live** trading. The system connects locally to IB Gateway or TWS.
2. **Strategy Settings Definition:** Users define:
   * **Contract Specifications:** Expiry (e.g., 0DTE, 1DTE, Current Week), Candle Timeframe.
   * **Delta Thresholds:** Target delta for finding strikes (e.g., `0.35` for Calls, `-0.35` for Puts).
   * **Risk Limits:** Max Trades Per Day, Daily Profit Target ($), and Daily Stop Loss ($).
   * **SL/TP Targets:** Mode selection between `Dynamic (ATR-based)` or `Fixed (% of premium)`, with optional `Trailing take-profit` pullbacks.
3. **Execution Pipeline:** 
   * The Python trading sidecar actively fetches live ticks.
   * On detecting entry indicators (SuperTrend reversals, engulfing + ATR confirmation), it fetches the Option Chain.
   * It calculates the exact strike based on the requested Delta.
   * A BUY order is transmitted to the Interactive Brokers API.
4. **Real-Time Monitoring:** 
   * The UI dashboard streams live ticks over JSON-RPC.
   * Active Positions display the `Current Price`, `Bid/Ask`, and live `P&L` dynamically.
   * The Trade Blotter updates the history of trades and cross-references them to live prices when active.
5. **Exit Logic:** 
   * Positions are exited fully automatically when they hit the configured Take Profit, Stop Loss, or Pullback Trailing thresholds.
   * Users can also intervene manually via a "Close Position" or global "Emergency Stop" button in the UI.

## Key Features & User Interface
* **Dashboard:** Features live trading controls (Start, Stop, Emergency Close), live connection status, and real-time activity logs.
* **Analytics:** Interactive visual charts including Win/Loss distributions (donut chart), P&L distribution (bar chart), and an Equity Curve area chart to track long-term performance.
* **Positions Tab:** Split into Active Positions (live dynamic prices) and Trade Blotter (historical record of executed entries and exits).
* **Logs Viewer:** A categorized, filterable system log viewer tracking INFO, WARN, ERROR, and DEBUG messages.
* **Licensing System:** A protective gate powered by Rust that uses a hardware-derived AES-256 fingerprint to validate subscription tiers (Basic, Pro, Enterprise) before allowing access to live trading.

## Legacy Compatibility
The product ships with its original PyQt5 interface (Legacy GUI) preserved as an alternative runtime. However, the core focus and future path lie in the high-performance Tauri + React application which wraps the exact same battle-tested Python trading logic.
