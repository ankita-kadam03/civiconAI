import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { IncidentCard } from "../../components/incidents";
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

function verificationHint(item: Complaint) {
  const yes = item.counters?.yes ?? 0;
  const no = item.counters?.no ?? 0;
  if (!yes && !no) return null;
  return `${yes} confirmed fixed · ${no} still an issue`;
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
    <div className="-mx-1 flex gap-3 overflow-x-auto pb-2">
      {columns.map(([title, rows]) => (
        <Card key={title} className="min-w-[15rem] max-w-[15rem] shrink-0 space-y-2 bg-white/80 p-3 dark:bg-slate-900/80">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-bold">{title}</h2>
            <span className="rounded-full bg-lavender px-2 py-0.5 text-xs font-semibold">{rows.length}</span>
          </div>
          <div className="max-h-[32rem] space-y-2 overflow-y-auto pr-0.5">
            {rows.length ? (
              rows.slice(0, 12).map((item) => (
                <div key={item.id} className="space-y-1.5 rounded-2xl border border-navy/5 bg-white/90 p-2 dark:border-white/10 dark:bg-slate-900">
                  <IncidentCard incident={item} to={href(item.id)} />
                  {title === "Verification" && verificationHint(item) ? (
                    <p className="px-1 text-[11px] font-medium text-teal">{verificationHint(item)}</p>
                  ) : null}
                  <SlaTimer ack={item.sla?.ack_due} resolve={item.sla?.resolve_due} />
                  {title === "New" ? (
                    <Button
                      type="button"
                      variant="ghost"
                      className="h-8 w-full py-0 text-xs"
                      onClick={async () => {
                        try {
                          await endpoints.claim(item.id);
                          toast("Added to your board");
                        } catch (err) {
                          toast(err instanceof Error ? err.message : "Could not claim", "err");
                        }
                      }}
                    >
                      Claim
                    </Button>
                  ) : null}
                </div>
              ))
            ) : (
              <p className="text-xs text-navy/50">Nothing here.</p>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}

export function ActiveReportCarousel({ items, href }: { items: Complaint[]; href: (id: string) => string }) {
  const [index, setIndex] = useState(0);
  const open = items.filter((i) => !["CLOSED", "REJECTED", "closed"].includes(i.status || ""));
  const list = open.length ? open : items;
  if (!list.length) {
    return <p className="text-sm text-navy/50 dark:text-slate-500">No open reports</p>;
  }
  const item = list[index % list.length];
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Button type="button" variant="ghost" className="h-8 w-8 p-0" aria-label="Previous" onClick={() => setIndex((i) => (i - 1 + list.length) % list.length)}>
          <ChevronLeft size={18} />
        </Button>
        <p className="text-xs font-semibold text-navy/50">
          {index + 1} / {list.length}
        </p>
        <Button type="button" variant="ghost" className="h-8 w-8 p-0" aria-label="Next" onClick={() => setIndex((i) => (i + 1) % list.length)}>
          <ChevronRight size={18} />
        </Button>
      </div>
      <IncidentCard incident={item} to={href(item.id)} />
    </div>
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
  const mine = items.filter((i) => bucketIncident(i, user?.id) === "Mine" || i.claimed_by === user?.id);
  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-mint via-white to-sky">
        <p className="text-sm font-semibold text-teal">Level 1 · local inbox</p>
        <h1 className="mt-1 text-3xl font-extrabold">Neighbourhood board</h1>
        <p className="mt-2 text-navy/70">
          Signed in as {user?.role?.replaceAll("_", " ") || "officer"}
          {user?.locality ? ` · ${user.locality}` : ""}. All Tambaram reports are visible — claim work and keep updates short.
        </p>
      </Card>
      <Card className="space-y-3">
        <h2 className="text-lg font-bold">Active report</h2>
        <ActiveReportCarousel items={mine.length ? mine : items} href={(id) => `/officer/incidents/${id}`} />
      </Card>
      {items.length ? <Kanban items={items} href={(id) => `/officer/incidents/${id}`} /> : <EmptyState title="Inbox is clear" body="New reports will appear here for all L1 officers." />}
    </div>
  );
}

export function L2Board() {
  const { user } = useAuth();
  const [items, setItems] = useState<Complaint[]>([]);
  useEffect(() => {
    endpoints
      .complaints("?page_size=80")
      .then((res) => setItems(res.items))
      .catch(() => setItems([]));
  }, []);
  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-lavender via-white to-peach">
        <p className="text-sm font-semibold text-teal">Level 2 · regional oversight</p>
        <h1 className="text-3xl font-extrabold">Regional board</h1>
        <p className="mt-2 text-navy/70">All municipal reports are listed. Completed only after the reporter confirms the fix.</p>
      </Card>
      <Card className="space-y-3">
        <h2 className="text-lg font-bold">Active report</h2>
        <ActiveReportCarousel items={items} href={(id) => `/l2/incidents/${id}`} />
      </Card>
      {items.length ? <Kanban items={items} href={(id) => `/l2/incidents/${id}`} /> : <EmptyState title="No reports yet" body="Reports will appear here for all L2 officers." />}
    </div>
  );
}

export function L3Board() {
  const [items, setItems] = useState<Complaint[]>([]);
  useEffect(() => {
    endpoints
      .complaints("?page_size=80")
      .then((res) => setItems(res.items))
      .catch(() => setItems([]));
  }, []);
  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-peach via-white to-sky">
        <p className="text-sm font-semibold text-teal">Level 3 · municipal</p>
        <h1 className="text-3xl font-extrabold">Municipal board</h1>
        <p className="mt-2 text-navy/70">Full visibility across Tambaram. Verification waits on citizen approval before Completed.</p>
      </Card>
      <Card className="space-y-3">
        <h2 className="text-lg font-bold">Active report</h2>
        <ActiveReportCarousel items={items} href={(id) => `/l3/incidents/${id}`} />
      </Card>
      {items.length ? <Kanban items={items} href={(id) => `/l3/incidents/${id}`} /> : <EmptyState title="No reports yet" body="Reports will appear here for L3." />}
    </div>
  );
}
