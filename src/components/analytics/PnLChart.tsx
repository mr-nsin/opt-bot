import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTradingStore } from "@/stores/tradingStore";

const tooltipStyle = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "8px",
  fontSize: "12px",
  padding: "8px 12px",
};

export function PnLChart() {
  const { todayTrades } = useTradingStore();
  const chartData = todayTrades.filter((t) => t.pnl !== undefined).map((t, i) => ({ name: `#${i + 1}`, pnl: t.pnl ?? 0, symbol: t.symbol }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">P&L Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-56 flex items-center justify-center text-xs text-muted-foreground">No completed trades yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.5} />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`$${v.toFixed(2)}`, "P&L"]} />
              <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                {chartData.map((e, i) => <Cell key={i} fill={e.pnl >= 0 ? "#10b981" : "#ef4444"} fillOpacity={0.85} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
