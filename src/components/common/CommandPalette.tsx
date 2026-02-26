import { useState, useEffect, useRef, useCallback, memo } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  BarChart3,
  Briefcase,
  FileText,
  Settings,
  Search,
  Command,
  Moon,
  Sun,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/hooks/useTheme";
import { formatHotkey } from "@/hooks/useHotkeys";

interface CommandItem {
  id: string;
  label: string;
  shortcut?: string;
  icon: React.ComponentType<{ className?: string }>;
  group: string;
  action: () => void;
}

/**
 * CommandPalette — A spotlight/cmdk-style command palette.
 * Opens with Ctrl+K, allows quick navigation and actions.
 * Inspired by VS Code command palette, Linear, and Raycast.
 */
export const CommandPalette = memo(function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { isDark, toggleTheme } = useTheme();

  // Command definitions
  const commands: CommandItem[] = [
    {
      id: "nav-dashboard",
      label: "Go to Dashboard",
      shortcut: formatHotkey("1"),
      icon: LayoutDashboard,
      group: "Navigation",
      action: () => navigate("/"),
    },
    {
      id: "nav-analytics",
      label: "Go to Analytics",
      shortcut: formatHotkey("2"),
      icon: BarChart3,
      group: "Navigation",
      action: () => navigate("/analytics"),
    },
    {
      id: "nav-positions",
      label: "Go to Positions",
      shortcut: formatHotkey("3"),
      icon: Briefcase,
      group: "Navigation",
      action: () => navigate("/positions"),
    },
    {
      id: "nav-logs",
      label: "Go to Logs",
      shortcut: formatHotkey("4"),
      icon: FileText,
      group: "Navigation",
      action: () => navigate("/logs"),
    },
    {
      id: "nav-settings",
      label: "Go to Settings",
      shortcut: formatHotkey("5"),
      icon: Settings,
      group: "Navigation",
      action: () => navigate("/settings"),
    },
    {
      id: "toggle-theme",
      label: isDark ? "Switch to Light Mode" : "Switch to Dark Mode",
      icon: isDark ? Sun : Moon,
      group: "Actions",
      action: toggleTheme,
    },
  ];

  // Filter commands by query
  const filtered = query
    ? commands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.group.toLowerCase().includes(query.toLowerCase())
      )
    : commands;

  // Group filtered results
  const groups = filtered.reduce(
    (acc, cmd) => {
      if (!acc[cmd.group]) acc[cmd.group] = [];
      acc[cmd.group].push(cmd);
      return acc;
    },
    {} as Record<string, CommandItem[]>
  );

  // Open/close handlers
  useEffect(() => {
    const onOpen = () => {
      setOpen(true);
      setQuery("");
      setSelectedIndex(0);
    };
    const onClose = () => setOpen(false);

    window.addEventListener("quantdrift:command-palette", onOpen);
    window.addEventListener("quantdrift:escape", onClose);
    return () => {
      window.removeEventListener("quantdrift:command-palette", onOpen);
      window.removeEventListener("quantdrift:escape", onClose);
    };
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Keyboard navigation
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && filtered[selectedIndex]) {
        e.preventDefault();
        filtered[selectedIndex].action();
        setOpen(false);
      } else if (e.key === "Escape") {
        e.preventDefault();
        setOpen(false);
      }
    },
    [filtered, selectedIndex]
  );

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!open) return null;

  let flatIndex = -1;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
      onClick={() => setOpen(false)}
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-background/60 backdrop-blur-sm animate-overlay" />

      {/* Palette */}
      <div
        className="relative w-full max-w-lg bg-card border border-border rounded-xl shadow-elevated animate-dialog overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 border-b border-border/50">
          <Search className="h-4 w-4 text-muted-foreground/50 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            className="flex-1 py-3 bg-transparent text-sm outline-none placeholder:text-muted-foreground/40"
          />
          <kbd className="hidden sm:flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-muted text-2xs text-muted-foreground font-mono">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[300px] overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <div className="py-6 text-center text-xs text-muted-foreground/50">
              No commands found
            </div>
          ) : (
            Object.entries(groups).map(([group, items]) => (
              <div key={group}>
                <p className="text-2xs font-semibold text-muted-foreground/50 uppercase tracking-wider px-2 py-1.5">
                  {group}
                </p>
                {items.map((cmd) => {
                  flatIndex++;
                  const isSelected = flatIndex === selectedIndex;
                  const Icon = cmd.icon;

                  return (
                    <button
                      key={cmd.id}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                        isSelected
                          ? "bg-primary/10 text-primary"
                          : "text-foreground/80 hover:bg-muted/50"
                      )}
                      onClick={() => {
                        cmd.action();
                        setOpen(false);
                      }}
                      onMouseEnter={() => setSelectedIndex(flatIndex)}
                    >
                      <Icon
                        className={cn(
                          "h-4 w-4 shrink-0",
                          isSelected ? "text-primary" : "text-muted-foreground/60"
                        )}
                      />
                      <span className="flex-1 text-left">{cmd.label}</span>
                      {cmd.shortcut && (
                        <kbd className="text-2xs font-mono text-muted-foreground/40 bg-muted/50 px-1.5 py-0.5 rounded">
                          {cmd.shortcut}
                        </kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-border/30 text-2xs text-muted-foreground/40">
          <div className="flex items-center gap-2">
            <Command className="h-3 w-3" />
            <span>Command Palette</span>
          </div>
          <div className="flex items-center gap-2">
            <kbd className="px-1 py-0.5 rounded bg-muted/50 font-mono">↑↓</kbd>
            <span>navigate</span>
            <kbd className="px-1 py-0.5 rounded bg-muted/50 font-mono">↵</kbd>
            <span>select</span>
          </div>
        </div>
      </div>
    </div>
  );
});
