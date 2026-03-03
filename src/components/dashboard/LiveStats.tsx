import { memo } from "react";
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

export const LiveStats = memo(function LiveStats() {
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const openTrades = useTradingStore((s) => s.openTrades);
  const closedTrades = useTradingStore((s) => s.closedTrades);
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);
  const status = useTradingStore((s) => s.status);
  const connectedToTws = useTradingStore((s) => s.connectedToTws);

  const wr = closedTrades > 0 ? winRate(winningTrades, closedTrades) : "0%";
  const wrPercent = closedTrades > 0 ? (winningTrades / closedTrades) * 100 : 0;
  const isRunning = status === "Running";
  const isIdle = status === "Idle";
  const isStarting = status === "Starting";

  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
      <StatCard
        title="Daily P&L"
        value={dailyPnl.total}
        isCurrency
        icon={DollarSign}
        trend={dailyPnl.total > 0 ? "up" : dailyPnl.total < 0 ? "down" : "neutral"}
        flash={isRunning}
        loading={isStarting}
        info="Total daily profit & loss"
      />
      <StatCard
        title="Realized"
        value={dailyPnl.realized}
        isCurrency
        icon={TrendingUp}
        trend={dailyPnl.realized > 0 ? "up" : dailyPnl.realized < 0 ? "down" : "neutral"}
        flash={isRunning}
        loading={isStarting}
        info="Closed trade P&L"
      />
      <StatCard
        title="Unrealized"
        value={dailyPnl.unrealized}
        isCurrency
        icon={TrendingDown}
        trend={dailyPnl.unrealized > 0 ? "up" : dailyPnl.unrealized < 0 ? "down" : "neutral"}
        flash={isRunning}
        loading={isStarting}
        info="Open position P&L"
      />
      <StatCard
        title="Trades"
        value={totalTrades}
        icon={Target}
        subtitle={`${openTrades} open / ${closedTrades} closed`}
        loading={isStarting}
        info="Open positions and closed trades today"
      />
      <StatCard
        title="Win Rate"
        value={wr}
        icon={Percent}
        trend={wrPercent >= 50 ? "up" : wrPercent > 0 ? "down" : "neutral"}
        loading={isStarting}
        info="Win percentage"
      />
      <StatCard
        title="Engine"
        value={isRunning ? "Active" : isIdle ? "Idle" : typeof status === "string" ? status : "Error"}
        icon={Activity}
        trend={isRunning ? "up" : isIdle ? "neutral" : "down"}
        subtitle={connectedToTws ? "TWS connected" : "TWS disconnected"}
        loading={isStarting}
        info="Engine status"
      />
    </div>
  );
});
