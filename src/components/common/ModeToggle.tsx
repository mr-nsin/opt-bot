import { Badge } from "@/components/ui/badge";
import { useConfigStore } from "@/stores/configStore";

export function ModeToggle() {
  const { settings, updateSettings } = useConfigStore();
  const isLive = settings.trading_mode === "live";

  const toggle = () => {
    updateSettings({
      trading_mode: isLive ? "demo" : "live",
    });
  };

  return (
    <button
      onClick={toggle}
      className="cursor-pointer"
      title={`Switch to ${isLive ? "Demo" : "Live"} mode`}
    >
      <Badge
        variant={isLive ? "danger" : "secondary"}
        className="text-2xs font-bold uppercase tracking-wider px-2.5 py-0.5 gap-1.5"
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            isLive ? "bg-red-500 live-dot" : "bg-muted-foreground/30"
          }`}
        />
        {isLive ? "LIVE" : "DEMO"}
      </Badge>
    </button>
  );
}
