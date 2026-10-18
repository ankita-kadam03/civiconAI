import { Clock } from "lucide-react";
import { cx, formatDate } from "../../lib/format";

function remaining(iso?: string | null): { text: string; overdue: boolean } {
  if (!iso) return { text: "Not scheduled", overdue: false };
  const due = new Date(iso).getTime();
  if (Number.isNaN(due)) return { text: "Not scheduled", overdue: false };
  const diff = due - Date.now();
  if (diff <= 0) return { text: "Past due", overdue: true };
  const hours = Math.floor(diff / 36e5);
  const minutes = Math.floor((diff % 36e5) / 6e4);
  if (hours >= 24) return { text: `${Math.floor(hours / 24)}d ${hours % 24}h`, overdue: false };
  if (hours >= 1) return { text: `${hours}h ${minutes}m`, overdue: false };
  return { text: `${minutes}m`, overdue: false };
}

export function SlaTimer({
  ack,
  resolve,
  compact = false,
}: {
  ack?: string | null;
  resolve?: string | null;
  compact?: boolean;
}) {
  const ackRem = remaining(ack);
  const useResolve = ackRem.text === "Not scheduled" || ackRem.overdue;
  const primary = useResolve ? remaining(resolve) : ackRem;
  const dueIso = useResolve ? resolve : ack;

  if (compact) {
    return (
      <span
        className={cx(
          "inline-flex max-w-full items-center gap-1 rounded-md px-1.5 py-0.5 font-medium tabular-nums",
          primary.overdue
            ? "bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300"
            : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
          "text-[9px] leading-none",
        )}
        title={dueIso ? `Due ${formatDate(dueIso)}` : undefined}
      >
        <Clock size={10} className="shrink-0 opacity-80" aria-hidden />
        {primary.overdue ? "SLA overdue" : `SLA ${primary.text}`}
      </span>
    );
  }

  return (
    <p
      className={cx(
        "inline-flex items-center gap-1.5 text-xs font-semibold",
        primary.overdue ? "text-rose-600 dark:text-rose-400" : "text-teal",
      )}
    >
      <Clock size={14} aria-hidden />
      {primary.overdue ? "Response past due" : `Response due in ${primary.text}`}
      {dueIso ? <span className="font-normal text-navy/50">· {formatDate(dueIso)}</span> : null}
    </p>
  );
}
