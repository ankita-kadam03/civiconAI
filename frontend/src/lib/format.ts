import type { Status, Severity } from "./types";

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function statusLabel(status?: string): string {
  const key = (status || "").toUpperCase();
  const labels: Record<string, string> = {
    SUBMITTED: "Submitted",
    ACKNOWLEDGED: "Acknowledged",
    IN_PROGRESS: "In progress",
    MORE_INFO_REQUESTED: "More info requested",
    ESCALATED: "Escalated",
    RESOLVED: "Resolved",
    CLOSED: "Closed",
    REJECTED: "Rejected",
  };
  if (labels[key]) return labels[key];
  return (status || "").replaceAll("_", " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}

export const PUBLIC_STATUS_FILTERS: Array<{ value: string; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "ACKNOWLEDGED", label: "Acknowledged" },
  { value: "IN_PROGRESS", label: "In progress" },
  { value: "MORE_INFO_REQUESTED", label: "More info requested" },
  { value: "ESCALATED", label: "Escalated" },
  { value: "RESOLVED", label: "Resolved" },
  { value: "CLOSED", label: "Closed" },
  { value: "REJECTED", label: "Rejected" },
];

export function statusTone(status?: Status | string): string {
  switch (status) {
    case "SUBMITTED":
      return "bg-lavender text-navy";
    case "ACKNOWLEDGED":
      return "bg-sky text-navy";
    case "IN_PROGRESS":
      return "bg-mint text-navy";
    case "MORE_INFO_REQUESTED":
      return "bg-peach text-navy";
    case "ESCALATED":
      return "bg-coral/70 text-navy";
    case "RESOLVED":
      return "bg-teal/15 text-teal";
    case "CLOSED":
      return "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-100";
    case "REJECTED":
      return "bg-rose-100 text-rose-800";
    case "reported":
    case "triaged":
      return "bg-lavender text-navy";
    case "assigned":
    case "in_progress":
    case "reopened":
      return "bg-mint text-navy";
    case "resolved_pending_verification":
      return "bg-peach text-navy";
    case "closed":
    case "closed_unverified":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export function severityTone(severity?: Severity | string): string {
  switch (severity) {
    case "LOW":
      return "bg-mint text-navy";
    case "MEDIUM":
      return "bg-sky text-navy";
    case "HIGH":
      return "bg-peach text-navy";
    case "CRITICAL":
      return "bg-coral text-navy";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function initials(name?: string): string {
  return (name || "?")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export const NEXT_STATUSES: Record<string, string[]> = {
  SUBMITTED: ["ACKNOWLEDGED", "REJECTED", "ESCALATED"],
  ACKNOWLEDGED: ["IN_PROGRESS", "MORE_INFO_REQUESTED", "REJECTED", "ESCALATED"],
  IN_PROGRESS: ["MORE_INFO_REQUESTED", "RESOLVED", "ESCALATED"],
  MORE_INFO_REQUESTED: ["IN_PROGRESS", "ACKNOWLEDGED", "REJECTED", "ESCALATED"],
  ESCALATED: ["ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "REJECTED"],
  RESOLVED: ["CLOSED", "IN_PROGRESS"],
  CLOSED: [],
  REJECTED: [],
  reported: ["ACKNOWLEDGED", "REJECTED"],
  triaged: ["IN_PROGRESS", "MORE_INFO_REQUESTED"],
  assigned: ["IN_PROGRESS", "ESCALATED"],
  in_progress: ["RESOLVED", "ESCALATED"],
  resolved_pending_verification: ["CLOSED", "IN_PROGRESS"],
  reopened: ["IN_PROGRESS", "ESCALATED"],
  closed: [],
  closed_unverified: [],
};
