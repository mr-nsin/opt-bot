# Product Context: QuantDrift Options Trading Bot

## Why This Product Exists
Options trading is highly time-sensitive. Traders need a tool that can monitor charts, parse technical setups, select contracts using strike/delta algorithms, and transmit orders to the broker in milliseconds.

QuantDrift bridges the gap between complex algorithmic options models and visual ease of use. It shields traders from the tedious process of manual calculation (e.g. tracking ATR pullbacks, manual delta-based strike selections) by automating execution directly through Interactive Brokers (IB).

## Target Users & Pain Points
* **Retail Options Day Traders:** Unable to monitor 10+ charts concurrently for breakout signals.
* **Algorithmic Traders:** Want to deploy technical strategies without writing a bespoke order routing interface from scratch.
* **Risk-Averse Investors:** Prone to emotional mistakes, needing strict drawdown limits and automated trailing stops enforced at the API layer.

## How it Works
1. **Selection:** Users pick symbols and toggle between **Demo** (paper) and **Live** trading.
2. **Strategy Settings:** Users define delta thresholds (e.g., `0.35` for Calls, `-0.35` for Puts) and set risk limits (Max Trades, Daily Profit Target, Daily Stop Loss).
3. **Execution:** The Python engine connects to IB Gateway/TWS, checks for entry indicators, fetches option chain chains, finds the matching delta contract, and fires a BUY order.
4. **Monitoring:** The UI streams real-time tick changes, dynamic premium updates, and position P&L in real-time.
5. **Exit:** Positions are exited automatically when they hit the target TP, SL, or pullback trailing thresholds.
