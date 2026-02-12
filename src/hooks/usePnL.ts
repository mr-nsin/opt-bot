import { useTradingStore } from "@/stores/tradingStore";
import { useTauriEvent } from "./useTauri";
import type { PnLEvent } from "@/lib/types";

export function usePnL() {
  const { dailyPnl, setDailyPnl } = useTradingStore();

  useTauriEvent<PnLEvent>("trading:pnl_update", (data) => {
    setDailyPnl({
      realized: data.realized_pnl,
      unrealized: data.unrealized_pnl,
      total: data.daily_pnl,
    });
  });

  return dailyPnl;
}
