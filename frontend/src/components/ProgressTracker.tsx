import { Check } from "lucide-react";
import { cx } from "../lib/format";

export function ProgressTracker({
  steps,
  current,
  className,
  orientation = "horizontal",
}: {
  steps: readonly string[];
  current: number;
  className?: string;
  orientation?: "horizontal" | "vertical";
}) {
  const allDone = current > steps.length;
  const capped = Math.min(Math.max(current, 1), steps.length);
  const idx = capped - 1;
  const pct = allDone ? 100 : steps.length <= 1 ? 100 : (idx / (steps.length - 1)) * 100;

  if (orientation === "vertical") {
    return (
      <div className={cx(className)}>
        <ol className="relative m-0 list-none p-0">
          {steps.map((label, i) => {
            const done = allDone || i < idx;
            const active = !allDone && i === idx;
            const last = i === steps.length - 1;
            return (
              <li key={label} className={cx("relative flex gap-3", !last && "pb-5")}>
                {!last ? (
                  <span
                    className="absolute left-[11px] top-6 bottom-0 w-0.5 bg-navy/12 dark:bg-white/15"
                    aria-hidden
                  />
                ) : null}
                <span
                  className={cx(
                    "relative z-[1] flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                    done && "bg-teal text-white",
                    active && !done && "bg-navy text-white dark:bg-teal dark:text-navy",
                    !done && !active && "bg-white text-navy/40 ring-1 ring-navy/15 dark:bg-slate-800 dark:text-slate-500",
                  )}
                >
                  {done ? <Check size={12} aria-hidden /> : i + 1}
                </span>
                <span
                  className={cx(
                    "min-w-0 pt-0.5 text-[11px] font-semibold leading-snug",
                    active ? "text-navy dark:text-white" : "text-navy/50 dark:text-slate-400",
                  )}
                >
                  {label}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  const stepCount = steps.length;

  return (
    <div className={cx("space-y-3", className)}>
      <div className="relative h-2 overflow-hidden rounded-full bg-navy/10 dark:bg-white/10">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-teal transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <ol
        className="grid list-none gap-1 p-0"
        style={{ gridTemplateColumns: `repeat(${stepCount}, minmax(0, 1fr))` }}
      >
        {steps.map((label, i) => {
          const done = allDone || i < idx;
          const active = !allDone && i === idx;
          return (
            <li key={label} className="flex min-w-0 flex-col items-center gap-1 text-center">
              <span
                className={cx(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                  done && "bg-teal text-white",
                  active && !done && "bg-navy text-white dark:bg-teal dark:text-navy",
                  !done && !active && "bg-white text-navy/40 ring-1 ring-navy/15 dark:bg-slate-800 dark:text-slate-500",
                )}
              >
                {done ? <Check size={14} aria-hidden /> : i + 1}
              </span>
              <span
                className={cx(
                  "w-full truncate px-0.5 text-[10px] font-semibold leading-tight sm:text-[11px]",
                  active ? "text-navy dark:text-white" : "text-navy/50 dark:text-slate-400",
                )}
                title={label}
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export const REPORT_PROGRESS_STEPS = ["Category", "Details", "Place", "Photos", "Review"] as const;

export const INCIDENT_PROGRESS_STEPS = ["Submitted", "Reviewed", "In progress", "Verification", "Completed"] as const;

export function incidentProgressIndex(status?: string): number {
  const s = (status || "").toUpperCase();
  if (s === "CLOSED" || s === "closed") return INCIDENT_PROGRESS_STEPS.length + 1;
  if (s === "RESOLVED" || s === "resolved_pending_verification") return 4;
  if (["IN_PROGRESS", "ESCALATED", "MORE_INFO_REQUESTED"].includes(s) || s === "IN_PROGRESS") return 3;
  if (s === "ACKNOWLEDGED") return 2;
  return 1;
}
