import { memo, useMemo } from "react";
import { TrendingUp, TrendingDown, Target, Award, DollarSign, BarChart3, Percent, Zap } from "lucide-react";
import { StatCard } from "@/components/common/StatCard";
import { useTradingStore } from "@/stores/tradingStore";
import { winRate } from "@/lib/utils";

export const PerformanceMetrics = memo(function PerformanceMetrics() {
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const todayTrades = useTradingStore((s) => s.todayTrades);

  const wr = winRate(winningTrades, totalTrades);
  const wrPercent = totalTrades === 0 ? 0 : (winningTrades / totalTrades) * 100;

  const stats = useMemo(() => {
    const wins = todayTrades.filter((t) => (t.pnl ?? 0) > 0);
    const losses = todayTrades.filter((t) => (t.pnl ?? 0) < 0);
    const avgWin = wins.reduce((s, t) => s + (t.pnl ?? 0), 0) / Math.max(1, wins.length) || 0;
    const avgLoss = losses.reduce((s, t) => s + (t.pnl ?? 0), 0) / Math.max(1, losses.length) || 0;
    const profitFactor = avgLoss !== 0 ? Math.abs(avgWin / avgLoss) : 0;
    const bestTrade = todayTrades.reduce((best, t) => Math.max(best, t.pnl ?? 0), 0);
    const worstTrade = todayTrades.reduce((worst, t) => Math.min(worst, t.pnl ?? 0), 0);
    // Expectancy = (WinRate * AvgWin) - (LossRate * |AvgLoss|)
    const winRatio = totalTrades === 0 ? 0 : winningTrades / totalTrades;
    const expectancy = winRatio * avgWin + (1 - winRatio) * avgLoss;

    return { avgWin, avgLoss, profitFactor, bestTrade, worstTrade, expectancy };
  }, [todayTrades, totalTrades, winningTrades]);

  const noData = totalTrades === 0;

  return (
    <div className="space-y-3">
      {/* Primary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <StatCard
          title="Total Trades"
          value={totalTrades}
          icon={Target}
          info="Total trades executed in this session"
        />
        <StatCard
          title="Win Rate"
          value={wr}
          icon={Award}
          trend={wrPercent >= 50 ? "up" : wrPercent > 0 ? "down" : "neutral"}
          info="Percentage of winning trades"
        />
        <StatCard
          title="Avg Win"
          value={stats.avgWin}
          isCurrency
          icon={TrendingUp}
          trend="up"
          info="Average profit on winning trades"
        />
        <StatCard
          title="Avg Loss"
          value={stats.avgLoss}
          isCurrency
          icon={TrendingDown}
          trend="down"
          info="Average loss on losing trades"
        />
        <StatCard
          title="Net P&L"
          value={dailyPnl.total}
          isCurrency
          icon={DollarSign}
          trend={dailyPnl.total >= 0 ? "up" : "down"}
          flash
          info="Net profit & loss for today"
        />
        <StatCard
          title="Profit Factor"
          value={stats.profitFactor > 0 ? stats.profitFactor.toFixed(2) : "N/A"}
          icon={BarChart3}
          trend={stats.profitFactor >= 1.5 ? "up" : stats.profitFactor > 0 ? "neutral" : "neutral"}
          info="Ratio of average win to average loss (>1.5 is good)"
        />
        <StatCard
          title="Best Trade"
          value={stats.bestTrade}
          isCurrency
          icon={Zap}
          trend="up"
          info="Highest single trade profit"
        />
        <StatCard
          title="Expectancy"
          value={noData ? "N/A" : `$${stats.expectancy.toFixed(2)}`}
          icon={Percent}
          trend={stats.expectancy > 0 ? "up" : stats.expectancy < 0 ? "down" : "neutral"}
          info="Expected profit per trade: (WinRate×AvgWin) - (LossRate×|AvgLoss|)"
        />
      </div>
    </div>
  );
});
