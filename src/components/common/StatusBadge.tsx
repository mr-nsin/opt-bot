import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  connected: boolean;
  label?: string;
  className?: string;
}

export function StatusBadge({ connected, label, className }: StatusBadgeProps) {
  return (
    <Badge
      variant={connected ? "success" : "danger"}
      className={cn("gap-1.5", className)}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          connected ? "bg-emerald-500 live-dot" : "bg-red-500"
        )}
      />
      {label || (connected ? "Connected" : "Disconnected")}
    </Badge>
  );
}
