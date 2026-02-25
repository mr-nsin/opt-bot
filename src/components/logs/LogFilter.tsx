import { Badge } from "@/components/ui/badge";
import { useLogStore } from "@/stores/logStore";

const LEVELS = ["INFO", "WARN", "ERROR", "DEBUG"];
const CATS = ["signal", "order", "position", "risk", "trading", "system"];

export function LogFilter() {
  const { filterLevel, filterCategory, setFilterLevel, setFilterCategory } = useLogStore();

  return (
    <div className="flex flex-wrap gap-4">
      <div className="flex items-center gap-1.5">
        <span className="text-2xs font-semibold text-muted-foreground uppercase tracking-wider mr-1">Level:</span>
        <Badge variant={filterLevel === null ? "default" : "secondary"} className="cursor-pointer text-2xs" onClick={() => setFilterLevel(null)}>All</Badge>
        {LEVELS.map((l) => (
          <Badge key={l} variant={filterLevel === l ? "default" : "secondary"} className="cursor-pointer text-2xs" onClick={() => setFilterLevel(filterLevel === l ? null : l)}>{l}</Badge>
        ))}
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-2xs font-semibold text-muted-foreground uppercase tracking-wider mr-1">Category:</span>
        <Badge variant={filterCategory === null ? "default" : "secondary"} className="cursor-pointer text-2xs" onClick={() => setFilterCategory(null)}>All</Badge>
        {CATS.map((c) => (
          <Badge key={c} variant={filterCategory === c ? "default" : "secondary"} className="cursor-pointer capitalize text-2xs" onClick={() => setFilterCategory(filterCategory === c ? null : c)}>{c}</Badge>
        ))}
      </div>
    </div>
  );
}
