import { Badge } from "@/components/ui/badge";
import { useLogStore } from "@/stores/logStore";
import {
  Info,
  AlertTriangle,
  XCircle,
  Bug,
  Target,
  ShoppingCart,
  Activity,
  ShieldAlert,
  Zap,
  Terminal,
} from "lucide-react";
import { cn } from "@/lib/utils";

const LEVELS = ["INFO", "WARN", "ERROR", "DEBUG"] as const;
const LEVEL_ICONS: Record<(typeof LEVELS)[number], typeof Info> = {
  INFO: Info,
  WARN: AlertTriangle,
  ERROR: XCircle,
  DEBUG: Bug,
};
const LEVEL_COLORS: Record<(typeof LEVELS)[number], string> = {
  INFO: "text-blue-500",
  WARN: "text-amber-500",
  ERROR: "text-red-500",
  DEBUG: "text-muted-foreground/60",
};
const CATS = ["signal", "order", "position", "risk", "trading", "system"] as const;
const CAT_ICONS: Record<(typeof CATS)[number], typeof Target> = {
  signal: Target,
  order: ShoppingCart,
  position: Activity,
  risk: ShieldAlert,
  trading: Zap,
  system: Terminal,
};
const CAT_COLORS: Record<(typeof CATS)[number], string> = {
  signal: "text-violet-500",
  order: "text-emerald-500",
  position: "text-cyan-500",
  risk: "text-amber-500",
  trading: "text-violet-400",
  system: "text-slate-400",
};

export function LogFilter() {
  const { filterLevel, filterCategory, setFilterLevel, setFilterCategory } =
    useLogStore();

  return (
    <div className="flex flex-wrap gap-4">
      <div className="flex items-center gap-1.5">
        <span className="text-2xs font-semibold text-muted-foreground uppercase tracking-wider mr-1">
          Level:
        </span>
        <Badge
          variant={filterLevel === null ? "default" : "secondary"}
          className="cursor-pointer text-2xs"
          onClick={() => setFilterLevel(null)}
        >
          All
        </Badge>
        {LEVELS.map((l) => {
          const Icon = LEVEL_ICONS[l];
          return (
            <Badge
              key={l}
              variant={filterLevel === l ? "default" : "secondary"}
              className="cursor-pointer text-2xs gap-1"
              onClick={() => setFilterLevel(filterLevel === l ? null : l)}
            >
              <Icon className={cn("h-3 w-3 shrink-0", LEVEL_COLORS[l])} />
              {l}
            </Badge>
          );
        })}
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-2xs font-semibold text-muted-foreground uppercase tracking-wider mr-1">
          Category:
        </span>
        <Badge
          variant={filterCategory === null ? "default" : "secondary"}
          className="cursor-pointer text-2xs"
          onClick={() => setFilterCategory(null)}
        >
          All
        </Badge>
        {CATS.map((c) => {
          const Icon = CAT_ICONS[c];
          return (
            <Badge
              key={c}
              variant={filterCategory === c ? "default" : "secondary"}
              className="cursor-pointer capitalize text-2xs gap-1"
              onClick={() => setFilterCategory(filterCategory === c ? null : c)}
            >
              <Icon className={cn("h-3 w-3 shrink-0", CAT_COLORS[c])} />
              {c}
            </Badge>
          );
        })}
      </div>
    </div>
  );
}
