import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  isCurrency?: boolean;
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  isCurrency,
  className,
}: StatCardProps) {
  const displayValue =
    isCurrency && typeof value === "number" ? formatCurrency(value) : String(value);
  const valueColor =
    isCurrency && typeof value === "number" ? pnlColor(value) : "";

  return (
    <Card className={cn("p-3.5", className)}>
      <div className="flex items-start justify-between mb-2">
        <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
          {title}
        </p>
        {Icon && (
          <div
            className={cn(
              "h-7 w-7 rounded-md flex items-center justify-center",
              trend === "up"
                ? "bg-emerald-500/10 text-emerald-500"
                : trend === "down"
                ? "bg-red-500/10 text-red-500"
                : "bg-muted text-muted-foreground"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </div>
        )}
      </div>
      <p className={cn("text-xl font-bold tabular-nums tracking-tight", valueColor)}>
        {displayValue}
      </p>
      {subtitle && (
        <p className="text-2xs text-muted-foreground mt-0.5">{subtitle}</p>
      )}
    </Card>
  );
}
