import { useRef, useEffect, useState, memo } from "react";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
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
  loading?: boolean;
  flash?: boolean;
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
      <div className={cn("rounded-lg border border-border/30 bg-card p-2.5 card-elevated", className)}>
        <div className="flex items-start justify-between mb-1">
          <Skeleton className="h-2 w-12" />
          <Skeleton className="h-5 w-5 rounded" />
        </div>
        <Skeleton className="h-4 w-16 mb-0.5" />
        <Skeleton className="h-2 w-10" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-border/30 bg-card p-2.5 group hover:border-border/50 transition-all duration-200 card-elevated",
        className
      )}
      title={info}
    >
      <div className="flex items-start justify-between mb-0.5">
        <p className="text-[9px] font-semibold text-muted-foreground/50 uppercase tracking-[0.08em]">
          {title}
        </p>
        {Icon && (
          <div
            className={cn(
              "h-5 w-5 rounded flex items-center justify-center",
              trend === "up"
                ? "bg-emerald-500/8 text-emerald-500"
                : trend === "down"
                  ? "bg-red-500/8 text-red-500"
                  : "bg-muted/50 text-muted-foreground/40"
            )}
          >
            <Icon className="h-2.5 w-2.5" />
          </div>
        )}
      </div>
      <p
        className={cn(
          "text-base font-bold font-mono tabular-nums tracking-tight rounded-sm px-0.5 transition-colors leading-tight",
          valueColor,
          flashClass,
          isCurrency && typeof value === "number" && value > 0 && "metric-profit",
          isCurrency && typeof value === "number" && value < 0 && "metric-loss"
        )}
      >
        {displayValue}
      </p>
      {subtitle && (
        <p className="text-[9px] text-muted-foreground/40 mt-0.5 font-medium">{subtitle}</p>
      )}
    </div>
  );
});
