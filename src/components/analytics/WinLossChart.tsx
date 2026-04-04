import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTradingStore } from "@/stores/tradingStore";

const tooltipStyle = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "8px",
  fontSize: "12px",
  padding: "8px 12px",
};

export function WinLossChart() {
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);
  const data = [
    { name: "Wins", value: winningTrades, color: "#10b981" },
    { name: "Losses", value: losingTrades, color: "#ef4444" },
  ];
  const total = winningTrades + losingTrades;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Win / Loss</CardTitle>
      </CardHeader>
      <CardContent>
        {total === 0 ? (
          <div className="h-56 flex items-center justify-center text-xs text-muted-foreground">No trades yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={data} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={4} dataKey="value" stroke="none">
                {data.map((e, i) => <Cell key={i} fill={e.color} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: "11px" }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
