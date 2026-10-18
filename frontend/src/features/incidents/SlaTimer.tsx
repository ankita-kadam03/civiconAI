import { formatDate } from "../../lib/format";

function remaining(iso?: string | null): string {
  if (!iso) return "No SLA";
  const due = new Date(iso).getTime();
  if (Number.isNaN(due)) return "No SLA";
  const diff = due - Date.now();
  if (diff <= 0) return "Overdue";
  const hours = Math.floor(diff / 36e5);
  const minutes = Math.floor((diff % 36e5) / 6e4);
  if (hours >= 24) return `${Math.floor(hours / 24)}d left`;
  if (hours >= 1) return `${hours}h ${minutes}m left`;
  return `${minutes}m left`;
}

export function SlaTimer({ ack, resolve }: { ack?: string | null; resolve?: string | null }) {
  const label = remaining(ack) === "Overdue" || remaining(ack) === "No SLA" ? remaining(resolve) : remaining(ack);
  const overdue = label === "Overdue";
  return (
    <p className={overdue ? "text-xs font-semibold text-rose-600" : "text-xs font-semibold text-teal"}>
      SLA {label}
      {ack ? ` · ack ${formatDate(ack)}` : ""}
    </p>
  );
}
