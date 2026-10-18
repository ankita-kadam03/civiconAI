import { useEffect } from "react";

export function usePolling(callback: () => void | Promise<void>, ms: number, enabled = true) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      await callback();
    };
    void tick();
    const id = window.setInterval(() => {
      void tick();
    }, ms);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [callback, enabled, ms]);
}
