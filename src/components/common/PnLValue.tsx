import { useRef, useEffect, useState, memo } from "react";
import { cn, formatCurrency } from "@/lib/utils";

interface PnLValueProps {
  value: number;
  /** Show +/- sign prefix */
  signed?: boolean;
  /** Show percentage alongside value */
  percent?: number;
  /** Additional CSS class */
  className?: string;
  /** Size variant */
  size?: "sm" | "md" | "lg" | "xl";
  /** Show label (e.g. "Daily P&L") */
  label?: string;
  /** Animate value changes with flash */
  flash?: boolean;
}

const sizeClasses = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-lg",
  xl: "text-2xl",
};

/**
 * Professional P&L value display with:
 * - Color coding (green/red/neutral)
 * - Flash animation on value change
 * - Tabular number formatting
 * - Optional label and percentage
 */
export const PnLValue = memo(function PnLValue({
  value,
  signed = true,
  percent,
  className,
  size = "md",
  label,
  flash = true,
}: PnLValueProps) {
  const prevValueRef = useRef(value);
  const [flashClass, setFlashClass] = useState("");

  useEffect(() => {
    if (!flash) return;
    const prev = prevValueRef.current;
    if (prev !== value) {
      const direction = value > prev ? "pnl-flash-profit" : value < prev ? "pnl-flash-loss" : "";
      if (direction) {
        setFlashClass(direction);
        const timer = setTimeout(() => setFlashClass(""), 600);
        return () => clearTimeout(timer);
      }
    }
    prevValueRef.current = value;
  }, [value, flash]);

  const colorClass =
    value > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : value < 0
        ? "text-red-600 dark:text-red-400"
        : "text-muted-foreground";

  const formatted = formatCurrency(value);
  const display = signed && value > 0 ? `+${formatted}` : formatted;

  return (
    <span className={cn("inline-flex items-baseline gap-1.5", className)}>
      {label && (
        <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </span>
      )}
      <span
        className={cn(
          "font-mono font-semibold tabular-nums rounded-sm px-0.5 transition-colors",
          sizeClasses[size],
          colorClass,
          flashClass
        )}
      >
        {display}
      </span>
      {percent !== undefined && (
        <span
          className={cn(
            "text-2xs font-mono tabular-nums opacity-70",
            colorClass
          )}
        >
          ({percent >= 0 ? "+" : ""}
          {percent.toFixed(1)}%)
        </span>
      )}
    </span>
  );
});
