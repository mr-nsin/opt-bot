# Project Brief: QuantDrift Options Trading Bot

## Core Requirements & Goals
QuantDrift is a professional-grade automated options trading bot. The goal is to provide retail and institutional options traders with a robust desktop application that:
1. **Automates Signal Detection:** Monitors a watchlist of active equities (e.g., SPY, QQQ, AAPL, TSLA) and executes options trades based on technical indicators (SuperTrend, engulfing candles, ATR).
2. **Manages Risk Real-Time:** Implements precise stop-loss (SL), take-profit (TP), and trailing targets directly linked to the options contract premium.
3. **Desktop shell wrapper:** Port the legacy PyQt5 interface to a modern, fast, cross-platform Tauri desktop shell with React and TypeScript.
4. **Maintains Reliability:** Retains the proven Python trading logic (`BOT.py` / `tws_api_client.py`) running in a low-overhead sidecar while managing UI interactions reactivity.
5. **Secure Licensing:** Provides hardware-bound, tamper-proof license validation implemented in compiled Rust.

## Problem Statement
The original PyQt5 GUI was difficult to maintain, lacked real-time aesthetic cues, and suffered from freezing UI threads during high-frequency API updates. The system must decouple the UI thread (React/Tauri) from the trade execution loop (Python sidecar) using standard input/output JSON-RPC pipes.

## Non-Negotiables
* **Real-time Price & P&L Updates:** Live bid/ask and P&L must stream continuously to both the Active Positions view and the Trade Blotter.
* **Safety Limits:** Daily max profit/loss drawdown limits and per-day maximum trade counts must halt all trading engines immediately upon violation.
* **Proven Math:** The ATR-based and fixed-percent option pricing algorithms must be mathematically verified and reliable.
