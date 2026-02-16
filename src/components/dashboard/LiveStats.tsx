import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  Percent,
} from "lucide-react";
import { StatCard } from "@/components/common/StatCard";
import { useTradingStore } from "@/stores/tradingStore";
import { winRate } from "@/lib/utils";

export function LiveStats() {
  const { dailyPnl, totalTrades, winningTrades, losingTrades } = useTradingStore();
  const wr = winRate(winningTrades, totalTrades);
  const wrPercent = totalTrades === 0 ? 0 : (winningTrades / totalTrades) * 100;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <StatCard
        title="Daily P&L"
        value={dailyPnl.total}
        isCurrency
        icon={DollarSign}
        trend={dailyPnl.total > 0 ? "up" : dailyPnl.total < 0 ? "down" : "neutral"}
      />
      <StatCard
        title="Realized"
        value={dailyPnl.realized}
        isCurrency
        icon={TrendingUp}
        trend={dailyPnl.realized > 0 ? "up" : dailyPnl.realized < 0 ? "down" : "neutral"}
      />
      <StatCard
        title="Unrealized"
        value={dailyPnl.unrealized}
        isCurrency
        icon={TrendingDown}
        trend={dailyPnl.unrealized > 0 ? "up" : dailyPnl.unrealized < 0 ? "down" : "neutral"}
      />
      <StatCard
        title="Trades"
        value={totalTrades}
        icon={Target}
        subtitle={`${winningTrades}W / ${losingTrades}L`}
      />
      <StatCard
        title="Win Rate"
        value={wr}
        icon={Percent}
        trend={wrPercent >= 50 ? "up" : wrPercent > 0 ? "down" : "neutral"}
      />
      <StatCard
        title="Engine"
        value={totalTrades > 0 ? "Active" : "Idle"}
        icon={Activity}
      />
    </div>
  );
}
