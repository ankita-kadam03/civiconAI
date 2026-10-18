import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button, Card, EmptyState, Skeleton } from "../../components/ui";
import { endpoints } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useToast } from "../../lib/toast";
import type { Complaint } from "../../lib/types";
import { SlaTimer } from "../incidents/SlaTimer";

function overdue(item: Complaint) {
  const due = item.sla?.ack_due || item.sla?.resolve_due;
  return Boolean(due && new Date(due).getTime() < Date.now() && !["CLOSED", "REJECTED", "closed"].includes(item.status || ""));
}

function bucketIncident(item: Complaint, userId?: string): string {
  if (overdue(item)) return "Overdue";
  if (item.status === "CLOSED" || item.status === "closed") return "Completed";
  if (item.status === "RESOLVED" || item.status === "resolved_pending_verification") return "Verification";
  if (item.claimed_by === userId || item.assigned_officer_id === userId) return "Mine";
  if (item.status === "IN_PROGRESS" || item.status === "ESCALATED" || item.status === "ACKNOWLEDGED") return "In progress";
  if (item.status === "SUBMITTED") return "New";
  return "In progress";
}

function KanbanCard({ item, href }: { item: Complaint; href: string }) {
  return (
    <Link
      to={href}
      className="block rounded-lg border border-navy/10 bg-white px-2 py-1.5 transition hover:border-teal/40 dark:border-white/10 dark:bg-slate-900"
    >
      <p className="truncate font-mono text-[10px] font-bold text-teal">{item.reference}</p>
      <p className="mt-0.5 line-clamp-2 text-[11px] font-semibold leading-snug text-navy dark:text-white">{item.title}</p>
      <p className="mt-1 truncate text-[10px] text-navy/55 dark:text-slate-400">{item.locality || "No locality"}</p>
      <div className="mt-1.5">
        <SlaTimer compact ack={item.sla?.ack_due} resolve={item.sla?.resolve_due} />
      </div>
    </Link>
  );
}

function KanbanColumn({
  title,
  rows,
  href,
  onClaim,
}: {
  title: string;
  rows: Complaint[];
  href: (id: string) => string;
  onClaim?: (id: string) => void;
}) {
  return (
    <div className="min-w-0 rounded-xl border border-navy/8 bg-white/70 p-2 dark:border-white/10 dark:bg-slate-900/50">
      <div className="mb-1.5 flex items-center justify-between gap-1 border-b border-navy/5 pb-1 dark:border-white/5">
        <h2 className="truncate text-[11px] font-bold uppercase tracking-wide text-navy/80 dark:text-slate-200">{title}</h2>
        <span className="rounded bg-lavender/80 px-1.5 py-0.5 text-[10px] font-bold tabular-nums">{rows.length}</span>
      </div>
      {rows.length ? (
        <ul className="flex flex-col gap-1.5">
          {rows.slice(0, 25).map((item) => (
            <li key={item.id}>
              <KanbanCard item={item} href={href(item.id)} />
              {title === "New" && onClaim ? (
                <Button
                  type="button"
                  variant="ghost"
                  className="mt-1 h-6 w-full py-0 text-[10px]"
                  onClick={(e) => {
                    e.preventDefault();
                    onClaim(item.id);
                  }}
                >
                  Claim
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="py-1 text-[10px] text-navy/40 dark:text-slate-500">—</p>
      )}
    </div>
  );
}

function Kanban({ items, href }: { items: Complaint[]; href: (id: string) => string }) {
  const toast = useToast();
  const { user } = useAuth();
  const buckets: Record<string, Complaint[]> = {
    New: [],
    Mine: [],
    "In progress": [],
    Verification: [],
    Completed: [],
    Overdue: [],
  };
  for (const item of items) {
    buckets[bucketIncident(item, user?.id)].push(item);
  }
  const columns: Array<[string, Complaint[]]> = [
    ["New", buckets.New],
    ["Mine", buckets.Mine],
    ["In progress", buckets["In progress"]],
    ["Verification", buckets.Verification],
    ["Completed", buckets.Completed],
    ["Overdue", buckets.Overdue],
  ];
  return (
    <div className="grid grid-cols-2 items-start gap-2 sm:grid-cols-3 lg:grid-cols-6">
      {columns.map(([title, rows]) => (
        <KanbanColumn
          key={title}
          title={title}
          rows={rows}
          href={href}
          onClaim={
            title === "New"
              ? async (id) => {
                  try {
                    await endpoints.claim(id);
                    toast("Added to your board");
                  } catch (err) {
                    toast(err instanceof Error ? err.message : "Could not claim", "err");
                  }
                }
              : undefined
          }
        />
      ))}
    </div>
  );
}

export function ActiveReportCarousel({ items, href }: { items: Complaint[]; href: (id: string) => string }) {
  const [index, setIndex] = useState(0);
  const open = items.filter((i) => !["CLOSED", "REJECTED", "closed"].includes(i.status || ""));
  const list = open.length ? open : items;
  if (!list.length) {
    return <p className="text-xs text-navy/50 dark:text-slate-500">No open reports</p>;
  }
  const item = list[index % list.length];
  const navBtn =
    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-navy/10 bg-white text-navy hover:bg-mint/40 disabled:opacity-30 dark:border-white/15 dark:bg-slate-800 dark:text-white";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-bold uppercase tracking-wide text-navy/50">
          Active · {index + 1}/{list.length}
        </span>
        <div className="flex gap-1">
          <button type="button" className={navBtn} aria-label="Previous" disabled={list.length < 2} onClick={() => setIndex((i) => (i - 1 + list.length) % list.length)}>
            <ChevronLeft size={16} aria-hidden />
          </button>
          <button type="button" className={navBtn} aria-label="Next" disabled={list.length < 2} onClick={() => setIndex((i) => (i + 1) % list.length)}>
            <ChevronRight size={16} aria-hidden />
          </button>
        </div>
      </div>
      <Link
        to={href(item.id)}
        className="block rounded-xl border border-navy/10 bg-white p-3 transition hover:border-teal/35 dark:border-white/10 dark:bg-slate-900"
      >
        <p className="font-mono text-[10px] font-bold text-teal">{item.reference}</p>
        <p className="mt-1 line-clamp-2 text-sm font-bold leading-snug text-navy dark:text-white">{item.title}</p>
        <p className="mt-1 truncate text-xs text-navy/60">{item.locality || "Location pending"}</p>
      </Link>
    </div>
  );
}

function BoardHero({ kicker, title, body }: { kicker: string; title: string; body: string }) {
  return (
    <Card className="bg-gradient-to-r from-mint via-white to-sky p-4 sm:p-5">
      <p className="text-xs font-semibold text-teal sm:text-sm">{kicker}</p>
      <h1 className="mt-1 text-2xl font-extrabold sm:text-3xl">{title}</h1>
      <p className="mt-2 text-sm text-navy/70">{body}</p>
    </Card>
  );
}

export function L1Board() {
  const { user } = useAuth();
  const [items, setItems] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    endpoints
      .complaints("?page_size=80")
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <Skeleton className="h-64" />;
  return (
    <div className="space-y-4 sm:space-y-6">
      <BoardHero
        kicker="Level 1 · local inbox"
        title="Neighbourhood board"
        body={`Signed in as ${user?.role?.replaceAll("_", " ") || "officer"}${user?.locality ? ` · ${user.locality}` : ""}. Claim new work and keep updates short.`}
      />
      {items.length ? <Kanban items={items} href={(id) => `/officer/incidents/${id}`} /> : <EmptyState title="Inbox is clear" body="New reports will appear here." />}
    </div>
  );
}

export function L2Board() {
  const [items, setItems] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    endpoints
      .complaints("?page_size=80")
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <Skeleton className="h-64" />;
  return (
    <div className="space-y-4 sm:space-y-6">
      <BoardHero
        kicker="Level 2 · regional oversight"
        title="Regional board"
        body="All municipal reports are listed. Completed only after the reporter confirms the fix."
      />
      {items.length ? <Kanban items={items} href={(id) => `/l2/incidents/${id}`} /> : <EmptyState title="No reports yet" body="Reports will appear here for L2 officers." />}
    </div>
  );
}

export function L3Board() {
  const [items, setItems] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    endpoints
      .complaints("?page_size=80")
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <Skeleton className="h-64" />;
  return (
    <div className="space-y-4 sm:space-y-6">
      <BoardHero
        kicker="Level 3 · municipal"
        title="Municipal board"
        body="Full visibility across the service area. Verification waits on citizen approval before Completed."
      />
      {items.length ? <Kanban items={items} href={(id) => `/l3/incidents/${id}`} /> : <EmptyState title="No reports yet" body="Reports will appear here for L3." />}
    </div>
  );
}
