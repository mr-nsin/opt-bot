import { useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";

/**
 * Global keyboard shortcuts for the trading app.
 *
 * Keyboard shortcuts are essential for professional trading terminals
 * (NinjaTrader, TradingView, Bloomberg all have extensive hotkey support).
 *
 * Current shortcuts:
 *   Ctrl+1 → Dashboard
 *   Ctrl+2 → Analytics
 *   Ctrl+3 → Positions
 *   Ctrl+4 → Logs
 *   Ctrl+5 → Settings
 *   Ctrl+K → Focus search (future: command palette)
 *   Escape → Close overlays
 */
export function useHotkeys() {
  const navigate = useNavigate();

  const handler = useCallback(
    (e: KeyboardEvent) => {
      // Skip when typing in input fields
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }

      const isCtrl = e.ctrlKey || e.metaKey;

      if (isCtrl) {
        switch (e.key) {
          case "1":
            e.preventDefault();
            navigate("/");
            break;
          case "2":
            e.preventDefault();
            navigate("/analytics");
            break;
          case "3":
            e.preventDefault();
            navigate("/positions");
            break;
          case "4":
            e.preventDefault();
            navigate("/logs");
            break;
          case "5":
            e.preventDefault();
            navigate("/settings");
            break;
          case "k":
          case "K":
            e.preventDefault();
            // Future: open command palette
            // For now, dispatch a custom event that components can listen to
            window.dispatchEvent(new CustomEvent("quantdrift:command-palette"));
            break;
        }
      }

      // Escape key — close any open dialogs/overlays
      if (e.key === "Escape") {
        window.dispatchEvent(new CustomEvent("quantdrift:escape"));
      }
    },
    [navigate]
  );

  useEffect(() => {
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handler]);
}

/**
 * Returns a formatted string for displaying hotkey hints.
 * Uses platform-appropriate modifier key symbol.
 */
export function formatHotkey(key: string): string {
  const isMac = navigator.platform?.toLowerCase().includes("mac");
  const mod = isMac ? "⌘" : "Ctrl";
  return `${mod}+${key}`;
}
