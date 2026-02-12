import { useState } from "react";
import { Plus, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useConfigStore } from "@/stores/configStore";

export function StockList() {
  const { tradingConfig, updateTradingConfig } = useConfigStore();
  const [newSymbol, setNewSymbol] = useState("");
  if (!tradingConfig) return null;

  const stocks = Object.keys(tradingConfig.stock_list_to_trade);

  const addStock = () => {
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol || stocks.includes(symbol)) return;
    updateTradingConfig({
      stock_list_to_trade: { ...tradingConfig.stock_list_to_trade, [symbol]: "NASDAQ" },
      stock_data: { ...tradingConfig.stock_data, [symbol]: { amount: 350 } },
    });
    setNewSymbol("");
  };

  const removeStock = (symbol: string) => {
    const newList = { ...tradingConfig.stock_list_to_trade };
    const newData = { ...tradingConfig.stock_data };
    delete newList[symbol];
    delete newData[symbol];
    updateTradingConfig({ stock_list_to_trade: newList, stock_data: newData });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Watchlist
        </CardTitle>
        <Badge variant="secondary" className="text-2xs">{stocks.length} symbols</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            placeholder="Add symbol..."
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && addStock()}
            className="flex-1 font-mono"
          />
          <Button size="sm" onClick={addStock} disabled={!newSymbol.trim()}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {stocks.map((symbol) => (
            <Badge key={symbol} variant="secondary" className="pl-2.5 pr-1 py-1 gap-1 group">
              <span className="font-mono font-semibold text-xs text-foreground">{symbol}</span>
              <span className="text-2xs text-muted-foreground font-mono">${tradingConfig.stock_data[symbol]?.amount || 350}</span>
              <button onClick={() => removeStock(symbol)} className="ml-0.5 h-4 w-4 rounded hover:bg-destructive/20 flex items-center justify-center opacity-40 group-hover:opacity-100 transition-opacity">
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
