import { HandHelping, MapPin } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";
import { Link } from "react-router-dom";
import { CategoryIconBadge } from "../lib/category-icons";
import type { Complaint } from "../lib/types";
import { cx, formatDate, severityTone, statusLabel, statusTone } from "../lib/format";
import { Button, Card } from "./ui";

function locationLine(incident: Complaint): string {
  if (incident.locality?.trim()) return incident.locality.trim();
  if (incident.address?.trim()) return incident.address.trim();
  if (incident.latitude != null && incident.longitude != null) {
    return `${incident.latitude.toFixed(5)}, ${incident.longitude.toFixed(5)}`;
  }
  return "Location not provided";
}

export function StatusBadge({ status }: { status?: string }) {
  return <span className={`chip ${statusTone(status)}`}>{statusLabel(status)}</span>;
}

export function SeverityBadge({ severity }: { severity?: string }) {
  return <span className={`chip ${severityTone(severity)}`}>{severity || "—"}</span>;
}

export function PromoteButton({
  promoted,
  count,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { promoted?: boolean; count?: number }) {
  return (
    <Button
      type="button"
      variant={promoted ? "primary" : "ghost"}
      className={cx(
        promoted ? "" : "border border-navy/15 bg-white shadow-sm hover:bg-mint/30 dark:border-white/15 dark:bg-slate-900/60",
        className,
      )}
      {...props}
    >
      <HandHelping size={16} className={promoted ? "fill-current" : ""} aria-hidden />
      {promoted ? "Promoted" : "Promote"}
      {count ? ` (${count})` : ""}
    </Button>
  );
}

export function IncidentCard({ incident, to }: { incident: Complaint; to: string }) {
  const iconKey = incident.category?.icon || incident.category?.slug;
  return (
    <Link to={to} className="block">
      <Card className="h-full transition hover:-translate-y-0.5 hover:shadow-card">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {incident.status ? <StatusBadge status={incident.status} /> : null}
          {incident.severity ? <SeverityBadge severity={incident.severity} /> : null}
        </div>
        <div className="flex items-start gap-3">
          <CategoryIconBadge slugOrIcon={iconKey} />
          <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-teal">{incident.reference}</p>
        <h3 className="mt-1 text-lg font-bold text-navy dark:text-white">{incident.title}</h3>
        {incident.summary || incident.description ? (
          <p className="mt-2 line-clamp-2 text-sm text-navy/70 dark:text-slate-300">{incident.summary || incident.description}</p>
        ) : null}
        <p className="mt-3 flex items-start gap-1.5 text-sm font-medium text-navy/80 dark:text-slate-200">
          <MapPin size={16} className="mt-0.5 shrink-0 text-teal" aria-hidden />
          <span>{locationLine(incident)}</span>
        </p>
        <p className="mt-2 text-xs text-navy/50">
          {incident.department?.name ? `${incident.department.name} · ` : ""}
          {incident.created_at ? `${formatDate(incident.created_at)} · ` : ""}
          Promotes: {incident.counters?.promotes ?? 0}
        </p>
          </div>
        </div>
      </Card>
    </Link>
  );
}

export function Timeline({ history }: { history?: Complaint["history"] }) {
  if (!history?.length) return <p className="text-sm text-navy/60">No status history yet.</p>;
  return (
    <ol className="space-y-4">
      {history.map((item, index) => (
        <li key={item.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className="mt-1 h-3 w-3 rounded-full bg-teal" />
            {index < history.length - 1 ? <span className="h-full w-px bg-mint" /> : null}
          </div>
          <div>
            <p className="font-semibold text-navy dark:text-white">{statusLabel(item.to_status)}</p>
            {item.note ? <p className="text-sm text-navy/70">{item.note}</p> : null}
            <p className="text-xs text-navy/50">{formatDate(item.created_at)}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
