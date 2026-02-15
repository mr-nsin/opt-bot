import { useState } from "react";
import { Plus, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useConfigStore } from "@/stores/configStore";
import { config as configApi } from "@/lib/tauri-commands";

export function StockList() {
  const { tradingConfig, updateTradingConfig } = useConfigStore();
  const [newSymbol, setNewSymbol] = useState("");
  if (!tradingConfig) return null;

  const stocks = Object.keys(tradingConfig.stock_list_to_trade || {});
  const exchanges = Object.values(tradingConfig.stock_list_to_trade || {});
  const allFutures = exchanges.length > 0 && exchanges.every((e) => e === "CME");
  const tradingType = allFutures ? "FUT" : "OPT";

  const persist = (next: typeof tradingConfig) => {
    updateTradingConfig(next);
    configApi.save(next).catch((e) => console.warn("Failed to save symbols:", e));
  };

  const exchangeForSymbol = (sym: string) =>
    /^[A-Z]+[A-Z]\d$/.test(sym) ? "CME" : "NASDAQ";

  const addStock = () => {
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol || stocks.includes(symbol)) return;
    const exchange = exchangeForSymbol(symbol);
    const next = {
      ...tradingConfig,
      stock_list_to_trade: { ...tradingConfig.stock_list_to_trade, [symbol]: exchange },
      stock_data: { ...tradingConfig.stock_data, [symbol]: { amount: 350 } },
    };
    persist(next);
    setNewSymbol("");
  };

  const removeStock = (symbol: string) => {
    const newList = { ...tradingConfig.stock_list_to_trade };
    const newData = { ...tradingConfig.stock_data };
    delete newList[symbol];
    delete newData[symbol];
    persist({ ...tradingConfig, stock_list_to_trade: newList, stock_data: newData });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Symbols to trade
        </CardTitle>
        <div className="flex items-center gap-1.5">
          <Badge variant={tradingType === "FUT" ? "default" : "secondary"} className="text-2xs" title={tradingType === "FUT" ? "Futures only (no options chain)" : "Stocks + options chain"}>
            {tradingType === "FUT" ? "Futures (FUT)" : "Options (OPT)"}
          </Badge>
          <Badge variant="secondary" className="text-2xs">{stocks.length} symbols</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-2xs text-muted-foreground">
          Sidecar subscribes to these symbols. FUT = futures only (e.g. MNQU5, NQU5). OPT = stocks + options (e.g. SPY, QQQ). Default: MNQU5 and NQU5 (both always included when either is present). If <code className="text-2xs bg-muted px-0.5 rounded">config/settings.json</code> exists, its symbols and broker are merged on startup.
        </p>
        <div className="flex gap-2">
          <Input
            placeholder="Add symbol (e.g. MNQU5, NQU5)..."
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
              <button
                onClick={() => removeStock(symbol)}
                disabled={stocks.length <= 1}
                title={stocks.length <= 1 ? "Keep at least one symbol" : "Remove symbol"}
                className="ml-0.5 h-4 w-4 rounded hover:bg-destructive/20 flex items-center justify-center opacity-40 group-hover:opacity-100 transition-opacity disabled:opacity-20 disabled:pointer-events-none"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
