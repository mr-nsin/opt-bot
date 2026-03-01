import { useEffect, useCallback, useRef } from "react";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

/** Listen to a Tauri event with automatic cleanup.
 * Uses a ref pattern so the handler can change without re-subscribing to the event.
 * Handles Strict Mode: if unmount runs before listen() resolves, we still unlisten when it does. */
export function useTauriEvent<T>(event: string, handler: (payload: T) => void) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    let cancelled = false;
    let unlisten: UnlistenFn | null = null;

    listen<T>(event, (e) => handlerRef.current(e.payload)).then((fn) => {
      if (cancelled) {
        fn();
        return;
      }
      unlisten = fn;
    });

    return () => {
      cancelled = true;
      if (unlisten) {
        unlisten();
        unlisten = null;
      }
    };
  }, [event]);
}

/** Listen to multiple Tauri events. Handles Strict Mode like useTauriEvent. */
export function useTauriEvents(
  events: Record<string, (payload: any) => void>
) {
  useEffect(() => {
    let cancelled = false;
    const unlisteners: UnlistenFn[] = [];

    Object.entries(events).forEach(([event, handler]) => {
      listen(event, (e) => handler(e.payload)).then((fn) => {
        if (cancelled) {
          fn();
          return;
        }
        unlisteners.push(fn);
      });
    });

    return () => {
      cancelled = true;
      unlisteners.forEach((fn) => fn());
    };
  }, []);
}
