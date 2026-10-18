import { cx } from "../../lib/format";

const STEPS = [
  ["reported", "Reported"],
  ["triaged", "Reviewed"],
  ["assigned", "Assigned"],
  ["in_progress", "In progress"],
  ["resolved_pending_verification", "Fixed?"],
  ["closed", "Closed"],
];

const FROM_LEGACY: Record<string, string> = {
  SUBMITTED: "reported",
  ACKNOWLEDGED: "triaged",
  IN_PROGRESS: "in_progress",
  RESOLVED: "resolved_pending_verification",
  CLOSED: "closed",
  ESCALATED: "in_progress",
  reopened: "in_progress",
};

export function JourneyLine({ status, level = 1 }: { status?: string; level?: number }) {
  const current = FROM_LEGACY[status || ""] || (status || "reported");
  const idx = Math.max(0, STEPS.findIndex(([key]) => key === current));
  return (
    <div>
      <ol className="flex flex-wrap gap-1">
        {STEPS.map(([key, label], i) => (
          <li
            key={key}
            className={cx(
              "rounded-full px-2 py-1 text-[11px] font-semibold",
              i <= idx ? "bg-navy text-white" : "bg-white text-navy/40",
            )}
          >
            {label}
          </li>
        ))}
      </ol>
      <p className="mt-2 text-xs font-semibold text-teal">Escalation L{level} of 3</p>
    </div>
  );
}
