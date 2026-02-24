import { useRef, useEffect, useState, memo } from "react";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  isCurrency?: boolean;
  className?: string;
  /** Show skeleton loading state */
  loading?: boolean;
  /** Flash the value when it changes */
  flash?: boolean;
  /** Additional info tooltip text */
  info?: string;
}

export const StatCard = memo(function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  isCurrency,
  className,
  loading,
  flash = false,
  info,
}: StatCardProps) {
  const displayValue =
    isCurrency && typeof value === "number" ? formatCurrency(value) : String(value);
  const valueColor =
    isCurrency && typeof value === "number" ? pnlColor(value) : "";

  // Flash animation on value change
  const prevRef = useRef(value);
  const [flashClass, setFlashClass] = useState("");

  useEffect(() => {
    if (!flash) return;
    const prev = prevRef.current;
    if (prev !== value && typeof value === "number" && typeof prev === "number") {
      const cls = value > prev ? "pnl-flash-profit" : value < prev ? "pnl-flash-loss" : "";
      if (cls) {
        setFlashClass(cls);
        const t = setTimeout(() => setFlashClass(""), 600);
        return () => clearTimeout(t);
      }
    }
    prevRef.current = value;
  }, [value, flash]);

  if (loading) {
    return (
      <Card className={cn("p-3.5", className)}>
        <div className="flex items-start justify-between mb-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-7 w-7 rounded-md" />
        </div>
        <Skeleton className="h-6 w-24 mb-1" />
        <Skeleton className="h-3 w-12" />
      </Card>
    );
  }

  return (
    <Card
      className={cn(
        "p-3.5 group hover:shadow-md transition-shadow duration-200",
        className
      )}
      title={info}
    >
      <div className="flex items-start justify-between mb-2">
        <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
          {title}
        </p>
        {Icon && (
          <div
            className={cn(
              "h-7 w-7 rounded-md flex items-center justify-center transition-colors",
              trend === "up"
                ? "bg-emerald-500/10 text-emerald-500"
                : trend === "down"
                  ? "bg-red-500/10 text-red-500"
                  : "bg-muted text-muted-foreground",
              "group-hover:scale-105 transition-transform duration-200"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </div>
        )}
      </div>
      <p
        className={cn(
          "text-xl font-bold tabular-nums tracking-tight rounded-sm px-0.5 transition-colors",
          valueColor,
          flashClass
        )}
      >
        {displayValue}
      </p>
      {subtitle && (
        <p className="text-2xs text-muted-foreground mt-0.5">{subtitle}</p>
      )}
    </Card>
  );
});
