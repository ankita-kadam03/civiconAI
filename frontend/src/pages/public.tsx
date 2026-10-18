import { MapPin } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { IncidentCard, PromoteButton, StatusBadge } from "../components/incidents";
import { CategoryIconBadge } from "../lib/category-icons";
import { formatDate } from "../lib/format";
import { useAuth } from "../lib/auth";
import { useToast } from "../lib/toast";
import { HomePreviewMap, IncidentMap } from "../components/maps";
import { Button, Card, EmptyState, Input, Skeleton, Textarea } from "../components/ui";
import { endpoints } from "../lib/api";
import { PUBLIC_STATUS_FILTERS } from "../lib/format";
import type { Complaint } from "../lib/types";

const LANDING_SECTION_IDS = ["explore", "how-it-works", "about", "help"] as const;

function scrollToLandingSection(id: string) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function useLandingHashScroll() {
  const location = useLocation();
  useEffect(() => {
    const hash = location.hash.replace(/^#/, "");
    if (!hash || !LANDING_SECTION_IDS.includes(hash as (typeof LANDING_SECTION_IDS)[number])) return;
    const t = window.setTimeout(() => scrollToLandingSection(hash), 50);
    return () => window.clearTimeout(t);
  }, [location.pathname, location.hash]);
}

function LandingSection({
  id,
  title,
  subtitle,
  children,
}: {
  id: string;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 space-y-4 border-t border-navy/5 pt-10 first:border-t-0 first:pt-0">
      <div>
        <h2 className="text-2xl font-extrabold text-navy dark:text-white md:text-3xl">{title}</h2>
        {subtitle ? <p className="mt-2 max-w-2xl text-navy/70 dark:text-slate-300">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}

function ExploreIncidentsBlock({ compact }: { compact?: boolean }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [items, setItems] = useState<Complaint[]>([]);
  const [view, setView] = useState<"list" | "map">("list");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    if (compact) params.set("page_size", "6");
    setLoading(true);
    endpoints
      .publicComplaints(`?${params.toString()}`)
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [q, status, compact]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Input placeholder="Search title, locality or CIV reference" value={q} onChange={(e) => setQ(e.target.value)} className="w-full sm:max-w-sm" />
        <select
          className="w-full min-w-0 rounded-2xl border border-navy/10 bg-white px-3 py-2.5 text-sm font-medium text-navy shadow-sm sm:min-w-[11rem] sm:w-auto dark:border-white/15 dark:bg-slate-900 dark:text-slate-100"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          aria-label="Filter by status"
        >
          {PUBLIC_STATUS_FILTERS.map((opt) => (
            <option key={opt.value || "all"} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {!compact ? (
          <div className="flex gap-2">
            <Button variant={view === "list" ? "primary" : "ghost"} onClick={() => setView("list")}>
              List
            </Button>
            <Button variant={view === "map" ? "primary" : "ghost"} onClick={() => setView("map")}>
              Map
            </Button>
          </div>
        ) : null}
      </div>
      {loading ? <Skeleton className="h-48" /> : null}
      {!loading && !compact && view === "map" ? <IncidentMap incidents={items} /> : null}
      {!loading && (compact || view === "list") ? (
        items.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {items.map((item) => (
              <IncidentCard key={item.id} incident={item} to={`/explore/${item.reference}`} />
            ))}
          </div>
        ) : (
          <EmptyState title="No public incidents yet" body="When neighbours share reports, they will appear here." />
        )
      ) : null}
    </div>
  );
}

export function HomePage() {
  useLandingHashScroll();

  const howSteps = [
    ["Notice something", "A pothole, a leak, a dark stretch of road."],
    ["Tell Civicon", "Add a photo, drop a pin, and send it in under a few minutes."],
    ["Follow along", "Every status change, assignment and escalation is timestamped."],
  ];

  const faqs = [
    ["Do I need an account?", "Yes, so you can track reports that belong to you and receive updates."],
    ["Does Civicon contact the municipality for me?", "No. Civicon records and routes reports. It never claims an agency was contacted automatically."],
    ["Why did an AI suggestion appear?", "Classification is a recommendation. Officers and you can ignore it."],
    ["Are photos public?", "Report photos can appear on public pages. Resolution evidence stays private."],
  ];

  return (
    <div className="space-y-10">
      <section className="grid items-center gap-8 md:grid-cols-[1.1fr_.9fr]">
        <div>
          <p className="chip bg-lavender text-navy">Civic reporting, made neighbourly</p>
          <h1 className="mt-4 text-4xl font-extrabold leading-[1.05] tracking-tight text-navy dark:text-white md:text-5xl">
            Your Neighbourhood.
            <br />
            Your Voice.
          </h1>
          <p className="mt-4 max-w-xl text-lg text-navy/70 dark:text-slate-300">
            Report potholes, leaks, and dark streets. Track updates on Google Maps — AI suggests categories; people stay in charge.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/signup">
              <Button>Report an issue</Button>
            </Link>
          </div>
        </div>
        <div className="space-y-4">
          <HomePreviewMap />
          <Card className="space-y-2 bg-gradient-to-br from-sky/40 via-white to-mint/40 p-4">
            <p className="text-sm font-bold text-teal">Three calm steps</p>
            <ol className="space-y-1 text-sm text-navy/75">
              <li>1. Notice — photo, text, or a pin.</li>
              <li>2. Track — SLA clocks and officer updates.</li>
              <li>3. Verify — neighbours confirm when the fix holds.</li>
            </ol>
          </Card>
        </div>
      </section>

      <LandingSection id="explore" title="Explore" subtitle="Public reports only. Private details stay with the people who need them.">
        <ExploreIncidentsBlock compact />
      </LandingSection>

      <LandingSection id="how-it-works" title="How it works" subtitle="From first report to verified resolution.">
        <div className="grid gap-4 md:grid-cols-3">
          {howSteps.map(([title, body], i) => (
            <Card key={title}>
              <p className="text-sm font-bold text-teal">Step {i + 1}</p>
              <h3 className="mt-2 text-xl font-bold">{title}</h3>
              <p className="mt-2 text-navy/70">{body}</p>
            </Card>
          ))}
        </div>
      </LandingSection>

      <LandingSection id="about" title="About Civicon AI">
        <div className="max-w-3xl space-y-4 text-navy/70 dark:text-slate-300">
          <p>
            Civicon AI is a civic issue reporting and escalation platform. Citizens file neighbourhood problems, officers update progress, and administrators keep service levels honest.
          </p>
          <p>
            AI can suggest a category, severity and department, but it never rejects or merges a report on its own. People stay in charge.
          </p>
        </div>
      </LandingSection>

      <LandingSection id="help" title="Help & FAQ">
        <div className="space-y-3">
          {faqs.map(([q, a]) => (
            <Card key={q}>
              <h3 className="font-bold">{q}</h3>
              <p className="mt-2 text-navy/70">{a}</p>
            </Card>
          ))}
        </div>
      </LandingSection>
    </div>
  );
}

export function ExplorePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold text-navy dark:text-white">Explore incidents</h1>
        <p className="text-navy/70">Public reports only. Private details stay with the people who need them.</p>
      </div>
      <ExploreIncidentsBlock />
    </div>
  );
}

export function PublicIncidentPage() {
  const { reference = "" } = useParams();
  const { user } = useAuth();
  const toast = useToast();
  const [item, setItem] = useState<Complaint | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [promoted, setPromoted] = useState(false);
  async function load() {
    const doc = await endpoints.publicComplaint(reference);
    setItem(doc);
    setPromoted(Boolean(doc.viewer_has_promoted));
  }
  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, [reference]);
  if (error) return <EmptyState title="Not found" body={error} />;
  if (!item) return <Skeleton className="h-64" />;
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card className="space-y-4 p-6 md:p-8">
        <div className="flex items-start gap-3">
          <CategoryIconBadge slugOrIcon={item.category?.icon || item.category?.slug} className="mt-1 h-11 w-11 rounded-2xl" size={22} />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold uppercase tracking-wide text-teal">{item.reference}</p>
            <h1 className="text-3xl font-extrabold text-navy dark:text-white">{item.title}</h1>
          </div>
        </div>
        <StatusBadge status={item.status} />
        <p className="text-base leading-relaxed text-navy/70 dark:text-slate-300">{item.description}</p>
        <p className="flex items-center gap-2 text-sm font-medium text-navy/80 dark:text-slate-200">
          <MapPin size={16} className="shrink-0 text-teal" aria-hidden />
          {item.locality}
        </p>
        {(item.comments || []).length ? (
          <div className="space-y-3 border-t border-navy/10 pt-4 dark:border-white/10">
            <h2 className="text-lg font-bold text-navy dark:text-white">Comments</h2>
            {(item.comments || []).map((c) => (
              <div key={c.id} className="rounded-2xl bg-foam p-3 text-sm dark:bg-slate-800/80">
                <p className="font-semibold text-navy dark:text-white">{c.author?.display_name || "Community member"}</p>
                <p className="mt-1 text-navy/80 dark:text-slate-200">{c.body}</p>
                <p className="mt-1 text-xs text-navy/50">{formatDate(c.created_at)}</p>
              </div>
            ))}
          </div>
        ) : null}
        {user ? (
          <div className="space-y-3 border-t border-navy/10 pt-4 dark:border-white/10">
            <PromoteButton
              promoted={promoted}
              count={item.counters?.promotes}
              onClick={async () => {
                try {
                  await endpoints.promote(item.id);
                  setPromoted(true);
                  toast("Promoted", "ok");
                  await load();
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Sign in to promote", "err");
                }
              }}
            />
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a public comment" />
            <Button
              type="button"
              onClick={async () => {
                if (!note.trim()) return;
                try {
                  await endpoints.comment(item.id, { body: note, is_internal: false });
                  setNote("");
                  toast("Comment posted", "ok");
                  await load();
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Could not comment", "err");
                }
              }}
            >
              Post comment
            </Button>
          </div>
        ) : (
          <p className="text-sm text-navy/60">
            <Link to="/login" className="font-semibold text-teal">
              Sign in
            </Link>{" "}
            to promote or comment on this issue.
          </p>
        )}
      </Card>
    </div>
  );
}

export function PrivacyPage() {
  return (
    <div className="max-w-3xl space-y-3 text-navy/75">
      <h1 className="text-4xl font-extrabold text-navy dark:text-white">Privacy</h1>
      <p>Public incident pages hide private addresses, internal notes and private attachments. Location is stored so officers can respond, not so strangers can visit your door.</p>
      <p>Passwords are hashed. Access tokens expire. Cloud credentials stay on the server. Browser map keys must be restricted by website and API.</p>
    </div>
  );
}

export function TermsPage() {
  return (
    <div className="max-w-3xl space-y-3 text-navy/75">
      <h1 className="text-4xl font-extrabold text-navy dark:text-white">Terms</h1>
      <p>Use Civicon AI to report genuine civic issues. Do not impersonate officials or upload unlawful content. Status updates describe the platform record, not a legal finding.</p>
    </div>
  );
}

export const landingNavSections = [
  { label: "Explore", hash: "explore" },
  { label: "How it works", hash: "how-it-works" },
  { label: "About", hash: "about" },
  { label: "Help", hash: "help" },
] as const;
