import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTradingStore } from "@/stores/tradingStore";

const tooltipStyle = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "8px",
  fontSize: "12px",
  padding: "8px 12px",
};

export function EquityCurve() {
  const todayTrades = useTradingStore((s) => s.todayTrades);
  let cum = 0;
  const data = todayTrades.filter((t) => t.pnl !== undefined).map((t, i) => { cum += t.pnl ?? 0; return { trade: i + 1, equity: cum }; });
  const pos = cum >= 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Equity Curve</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <div className="h-56 flex items-center justify-center text-xs text-muted-foreground">No completed trades yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={pos ? "#10b981" : "#ef4444"} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={pos ? "#10b981" : "#ef4444"} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.5} />
              <XAxis dataKey="trade" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`$${v.toFixed(2)}`, "Equity"]} />
              <Area type="monotone" dataKey="equity" stroke={pos ? "#10b981" : "#ef4444"} fill="url(#eqGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
