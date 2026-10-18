import { Check } from "lucide-react";
import { cx } from "../lib/format";

export function ProgressTracker({
  steps,
  current,
  className,
}: {
  steps: readonly string[];
  current: number;
  className?: string;
}) {
  const allDone = current > steps.length;
  const capped = Math.min(Math.max(current, 1), steps.length);
  const idx = capped - 1;
  const pct = allDone ? 100 : steps.length <= 1 ? 100 : (idx / (steps.length - 1)) * 100;

  return (
    <div className={cx("space-y-3", className)}>
      <div className="relative h-2 overflow-hidden rounded-full bg-navy/10 dark:bg-white/10">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-teal transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <ol className="flex flex-wrap justify-between gap-2">
        {steps.map((label, i) => {
          const done = allDone || i < idx;
          const active = !allDone && i === idx;
          return (
            <li
              key={label}
              className={cx(
                "flex min-w-0 flex-1 basis-[4.5rem] flex-col items-center gap-1 text-center",
                i === steps.length - 1 && "flex-none basis-auto",
              )}
            >
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
                  "line-clamp-2 text-[10px] font-semibold leading-tight sm:text-xs",
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
