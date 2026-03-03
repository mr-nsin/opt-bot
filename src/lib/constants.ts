export const CANDLE_TIMEFRAMES = [
  { value: "1 min", label: "1 min" },
  { value: "5 mins", label: "5 mins" },
  { value: "15 mins", label: "15 mins" },
  { value: "30 mins", label: "30 mins" },
  { value: "1 hour", label: "1 hour" },
];

/** For stocks (AMZN, AAPL, AMD, etc.) — weekly options expiry */
export const STOCK_EXPIRY_OPTIONS = [
  { value: "current", label: "Current week" },
  { value: "next", label: "Next week" },
];

/** For SPY, QQQ — daily options expiry */
export const SPY_QQQ_EXPIRY_OPTIONS = [
  { value: "0DTE", label: "0DTE" },
  { value: "1DTE", label: "1DTE" },
];
