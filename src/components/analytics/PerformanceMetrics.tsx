import { TrendingUp, TrendingDown, Target, Award, DollarSign, BarChart3 } from "lucide-react";
import { StatCard } from "@/components/common/StatCard";
import { useTradingStore } from "@/stores/tradingStore";
import { winRate } from "@/lib/utils";

export function PerformanceMetrics() {
  const { totalTrades, winningTrades, losingTrades, dailyPnl, todayTrades } = useTradingStore();
  const wr = winRate(winningTrades, totalTrades);
  const avgWin = todayTrades.filter((t) => (t.pnl ?? 0) > 0).reduce((s, t) => s + (t.pnl ?? 0), 0) / Math.max(1, winningTrades) || 0;
  const avgLoss = todayTrades.filter((t) => (t.pnl ?? 0) < 0).reduce((s, t) => s + (t.pnl ?? 0), 0) / Math.max(1, losingTrades) || 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <StatCard title="Total Trades" value={totalTrades} icon={Target} />
      <StatCard title="Win Rate" value={`${wr.toFixed(1)}%`} icon={Award} trend={wr >= 50 ? "up" : "down"} />
      <StatCard title="Avg Win" value={avgWin} isCurrency icon={TrendingUp} trend="up" />
      <StatCard title="Avg Loss" value={avgLoss} isCurrency icon={TrendingDown} trend="down" />
      <StatCard title="Net P&L" value={dailyPnl.total} isCurrency icon={DollarSign} trend={dailyPnl.total >= 0 ? "up" : "down"} />
      <StatCard title="Profit Factor" value={avgLoss !== 0 ? Math.abs(avgWin / avgLoss).toFixed(2) : "N/A"} icon={BarChart3} />
    </div>
  );
}
