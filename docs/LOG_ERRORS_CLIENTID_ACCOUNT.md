# Log errors: Client ID, account code, and startup errors

This doc explains the **errors at startup** in `trading-engine/logs/bot_YYYY-MM-DD.log`, especially around **client ID** and **account code**.

---

## What the log format means

Each line looks like:

```text
2026-02-22 00:40:43,634 - ERROR - 6809254 - Id: 10001, Code: 321, Msg: Error validating request.-'ci' : cause - Invalid account code
```

- **First number after ERROR** (e.g. `6809254`) = **thread ID** from the logging formatter (`%(thread_id)s` in `common.py`). It is **not** the TWS Client ID.
- **Id: 10001** = **request ID** used for a specific API call (e.g. PnL request).
- **Code / Msg** = TWS/IB error code and message.

---

## Main startup errors

### 1. `Id: 10001, Code: 321, 'ci' : cause - Invalid account code`

**What it is:**  
TWS is rejecting the **account code** used in the PnL request, not the TWS Client ID.

**Where it comes from:**  
In `BOT.py`, `init_order_requests()` calls:

```python
client.reqPnL(10001, SUB_ACCOUNT_ID, "")
```

`SUB_ACCOUNT_ID` is set from config as **`ACCOUNT_ID`** (e.g. in `config.json`: `"ACCOUNT_ID": "U6987141"`).  
TWS only accepts the account that belongs to the current login. If the logged-in TWS session uses a different account (e.g. **DU5690365** from “Using account for PnL” in the log), then **U6987141** can be invalid for this session and you get **Invalid account code**.

**Why it happens:**

- Config has an account that doesn’t match the TWS login (e.g. paper vs live, or wrong account id).
- Typo or old value in `ACCOUNT_ID` in config.

**What to do:**

1. In TWS/IB Gateway, confirm which account you’re logged into (e.g. DU5690365).
2. Set **`ACCOUNT_ID`** in your config (e.g. `config.json` or app Connection settings) to **that exact account string**.
3. Or leave it empty and rely on the account from TWS (see “Duplicate PnL and account summary” below).

---

### 2. `Id: -1, Code: 321, 'ct' : cause - The API interface is currently in Read-Only mode`

**What it is:**  
TWS/IB Gateway is in **read-only** mode. Some requests (e.g. orders, or certain account requests) are rejected.

**What to do:**  
In TWS: **Edit → Global Configuration → API → Settings** (or similar), and ensure **Read-Only API** is **disabled** if you need trading and full account access.

---

### 3. `Id: 1, Code: 10185, Msg: Failed to cancel PNL (not subscribed)`

**What it is:**  
The code tries to cancel a PnL subscription (reqId 1) before it was ever successfully subscribed (e.g. on a fresh connect or reconnect). TWS reports “not subscribed”.

**Why it’s usually harmless:**  
Right after, the client subscribes to PnL again (e.g. in `managedAccounts` with reqId 1). So this is often a one-off at connect. If you see it repeatedly with no successful PnL later, then connection or subscription order may need checking.

---

### 4. Duplicate PnL and account summary (reqId 1 vs 10001)

There are **two** PnL flows:

| Location              | Request ID | Account used                          |
|----------------------|-----------|----------------------------------------|
| `tws_api_client.py`  | **1**     | `managed_account` from TWS (correct)  |
| `BOT.py`             | **10001** | `SUB_ACCOUNT_ID` from config          |

- The **reqId 1** flow uses the account TWS reports in `managedAccounts` (e.g. DU5690365) and is the one used for continuous PnL and account summary in the app.
- The **reqId 10001** flow uses config’s `ACCOUNT_ID`. If that doesn’t match the logged-in account, you get **Invalid account code** for **Id: 10001**.

So the **clientid / account** error at startup is about the **account code** used for the **10001** PnL request, not about the TWS Client ID number. Fix by setting **ACCOUNT_ID** to the same account as in TWS (or aligning BOT to use the managed account for that request too).

---

## Later in the log: Code 504 “Not connected”, reconnects, etc.

- **Code 504, Msg: Not connected**  
  Requests (e.g. contract details, subscriptions) are sent while the connection is down or not ready. Usually seen during or right after reconnects.

- **TWS connection closed** / **Reconnect attempt N failed: 'NoneType' object has no attribute 'isConnected'**  
  The connection dropped and reconnection logic is running; sometimes the client object is in a bad state (e.g. None or not fully rebuilt), which causes the `NoneType` error.

- **Code 162, Trading TWS session is connected from a different IP address**  
  Another TWS session (same or different machine) connected and took over; only one API client per account is allowed from a given “session” in some configurations.

- **Code 10197, No market data during competing live session**  
  Market data is being used by another session (e.g. TWS GUI and API both requesting the same data).

These are connection/session/data issues, not “client ID” in the sense of the startup **Invalid account code** above.

---

## Summary

| Log / error                         | Meaning                                      | Action |
|------------------------------------|----------------------------------------------|--------|
| Number after ERROR (e.g. 6809254)   | Thread ID (not TWS Client ID)                | None   |
| Id: 10001, Code 321, Invalid account code | Config `ACCOUNT_ID` wrong for this TWS login | Set `ACCOUNT_ID` to the account shown in TWS (e.g. DU5690365) or match login |
| Code 321, Read-Only mode            | TWS API is read-only                         | Disable Read-Only API in TWS/IB Gateway |
| Id: 1, Code 10185, cancel PNL      | Cancel PnL before subscribe                   | Usually harmless at connect |

The **“clientid” / account error at startup** is the **Invalid account code** for **Id: 10001**: fix by correcting **ACCOUNT_ID** in config to match the account you’re logged into in TWS.
