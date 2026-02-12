import { useEffect, useCallback, useRef } from "react";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

/** Listen to a Tauri event with automatic cleanup.
 * Uses a ref pattern so the handler can change without re-subscribing to the event. */
export function useTauriEvent<T>(event: string, handler: (payload: T) => void) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    let unlisten: UnlistenFn | null = null;

    listen<T>(event, (e) => handlerRef.current(e.payload)).then((fn) => {
      unlisten = fn;
    });

    return () => {
      unlisten?.();
    };
  }, [event]);
}

/** Listen to multiple Tauri events */
export function useTauriEvents(
  events: Record<string, (payload: any) => void>
) {
  useEffect(() => {
    const unlisteners: UnlistenFn[] = [];

    Object.entries(events).forEach(([event, handler]) => {
      listen(event, (e) => handler(e.payload)).then((fn) => {
        unlisteners.push(fn);
      });
    });

    return () => {
      unlisteners.forEach((fn) => fn());
    };
  }, []);
}
