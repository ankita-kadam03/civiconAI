import { MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import type { Complaint } from "../lib/types";
import { formatDate, severityTone, statusLabel, statusTone } from "../lib/format";
import { Card } from "./ui";

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

export function IncidentCard({ incident, to }: { incident: Complaint; to: string }) {
  return (
    <Link to={to} className="block">
      <Card className="h-full transition hover:-translate-y-0.5 hover:shadow-card">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <StatusBadge status={incident.status} />
          <SeverityBadge severity={incident.severity} />
        </div>
        <p className="text-xs font-semibold uppercase tracking-wide text-teal">{incident.reference}</p>
        <h3 className="mt-1 text-lg font-bold text-navy dark:text-white">{incident.title}</h3>
        <p className="mt-2 line-clamp-2 text-sm text-navy/70 dark:text-slate-300">{incident.summary || incident.description}</p>
        <p className="mt-3 flex items-start gap-1.5 text-sm font-medium text-navy/80 dark:text-slate-200">
          <MapPin size={16} className="mt-0.5 shrink-0 text-teal" aria-hidden />
          <span>{locationLine(incident)}</span>
        </p>
        <p className="mt-2 text-xs text-navy/50">
          {incident.department?.name || "Civic desk"} · {formatDate(incident.created_at)}
        </p>
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
