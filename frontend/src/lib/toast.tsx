import { CheckCircle2, AlertCircle, Info } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { cx } from "./format";
import { promptPwaInstall } from "./pwa-install";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface ToastItem {
  id: number;
  title: string;
  tone: "ok" | "err" | "info";
  action?: ToastAction;
}

export type ToastOptions = {
  durationMs?: number;
  install?: boolean;
};

type ToastFn = (title: string, tone?: ToastItem["tone"], options?: ToastOptions) => void;

const DEFAULT_MS = 4200;
const INSTALL_TOAST_MS = 14_000;

const ToastContext = createContext<ToastFn>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const push = useCallback<ToastFn>((title, tone = "ok", options) => {
    const id = Date.now() + Math.random();
    const durationMs = options?.durationMs ?? (options?.install ? INSTALL_TOAST_MS : DEFAULT_MS);
    const action: ToastAction | undefined = options?.install
      ? {
          label: "Install",
          onClick: () => {
            void promptPwaInstall();
          },
        }
      : undefined;
    setItems((prev) => [...prev, { id, title, tone, action }]);
    window.setTimeout(() => dismiss(id), durationMs);
  }, [dismiss]);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed right-5 top-20 z-[80] flex w-[min(92vw,380px)] flex-col gap-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={cx(
              "pointer-events-auto rounded-2xl px-4 py-3 text-sm shadow-card",
              item.tone === "err" && "bg-rose-600 text-white",
              item.tone === "ok" && "bg-emerald-600 text-white",
              item.tone === "info" && "border border-navy/10 bg-white text-navy dark:border-white/10 dark:bg-slate-800 dark:text-slate-100",
            )}
          >
            <p className="flex items-start gap-2 leading-snug">
              {item.tone === "ok" ? (
                <CheckCircle2 size={18} className="mt-0.5 shrink-0" aria-hidden />
              ) : item.tone === "err" ? (
                <AlertCircle size={18} className="mt-0.5 shrink-0" aria-hidden />
              ) : (
                <Info size={18} className="mt-0.5 shrink-0 opacity-80" aria-hidden />
              )}
              <span>{item.title}</span>
            </p>
            {item.action ? (
              <button
                type="button"
                className={cx(
                  "mt-2.5 rounded-full px-4 py-1.5 text-xs font-bold transition",
                  item.tone === "info" && "bg-teal text-white hover:bg-teal/90",
                  item.tone === "ok" && "bg-white/20 text-white hover:bg-white/30",
                  item.tone === "err" && "bg-white/20 text-white hover:bg-white/30",
                )}
                onClick={() => {
                  item.action?.onClick();
                  dismiss(item.id);
                }}
              >
                {item.action.label}
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
