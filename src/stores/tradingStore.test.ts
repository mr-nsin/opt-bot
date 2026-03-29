import { describe, it, expect, beforeEach } from "vitest";
import { useTradingStore } from "./tradingStore";

describe("updateTradePnl (ISSUES_ROADMAP P2)", () => {
  beforeEach(() => {
    useTradingStore.getState().reset();
  });

  it("matches strike when event sends string and store has number", () => {
    useTradingStore.getState().addTrade({
      id: 1,
      symbol: "SPY",
      right: "C",
      strike: 500,
      expiry: "20260313",
      side: "BUY",
      quantity: 1,
      entry_price: 1.5,
      status: "open",
      timestamp: new Date().toISOString(),
    });
    // JSON from sidecar may deserialize strike as string
    useTradingStore.getState().updateTradePnl(
      { symbol: "SPY", right: "C", strike: "500" as unknown as number, expiry: "20260313" },
      42,
      2.0
    );
    const t = useTradingStore.getState().todayTrades[0];
    expect(t?.status).toBe("closed");
    expect(t?.pnl).toBe(42);
    expect(t?.exit_price).toBe(2.0);
  });

  it("matches CALL to C and normalizes expiry dashes", () => {
    useTradingStore.getState().addTrade({
      id: 2,
      symbol: "QQQ",
      right: "C",
      strike: 400,
      expiry: "2026-03-13",
      side: "BUY",
      quantity: 1,
      entry_price: 2,
      status: "open",
      timestamp: new Date().toISOString(),
    });
    useTradingStore.getState().updateTradePnl(
      { symbol: "QQQ", right: "CALL", strike: 400, expiry: "20260313" },
      -10,
      1.5
    );
    const t = useTradingStore.getState().todayTrades[0];
    expect(t?.status).toBe("closed");
    expect(t?.pnl).toBe(-10);
  });
});
