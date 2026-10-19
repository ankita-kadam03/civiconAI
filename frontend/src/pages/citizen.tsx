import { zodResolver } from "@hookform/resolvers/zod";
import { Bell, MapPin, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { ActiveReportCarousel, L1Board } from "../features/admin/Boards";
import { INCIDENT_PROGRESS_STEPS, ProgressTracker, REPORT_PROGRESS_STEPS, incidentProgressIndex } from "../components/ProgressTracker";
import { categoryIcon } from "../lib/category-icons";
import { notificationTabs } from "../features/auth/paths";
import { SlaTimer } from "../features/incidents/SlaTimer";
import { IncidentCard, PromoteButton, SeverityBadge, StatusBadge, Timeline } from "../components/incidents";
import { CategoryIconBadge } from "../lib/category-icons";
import { LocationPicker } from "../components/maps";
import { Button, Card, ConfirmDialog, EmptyState, Field, FileAttachButton, FileUpload, Input, Skeleton, Textarea } from "../components/ui";
import { endpoints, fetchAttachmentBlob } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useFileObjectUrls } from "../lib/file-previews";
import { NEXT_STATUSES, cx, formatDate } from "../lib/format";
import { reportSchema, type ReportValues } from "../lib/schemas";
import { useToast } from "../lib/toast";
import type { Category, Complaint, Department, NotificationItem, User } from "../lib/types";

export function CitizenDashboard() {
  const toast = useToast();
  const [items, setItems] = useState<Complaint[]>([]);
  const [nearby, setNearby] = useState<Complaint[]>([]);
  const [places, setPlaces] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [placeLabel, setPlaceLabel] = useState("Home");
  useEffect(() => {
    endpoints
      .complaints("?mine=true")
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
    endpoints.publicComplaints("?page_size=6").then((res) => setNearby(res.items)).catch(() => setNearby([]));
    endpoints.savedLocations().then((res) => setPlaces(res.items)).catch(() => setPlaces([]));
  }, []);
  const open = items.filter((i) => !["RESOLVED", "CLOSED", "REJECTED", "closed", "closed_unverified"].includes(i.status || ""));
  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-sky via-white to-mint">
        <p className="text-sm font-semibold text-teal">Good to see you</p>
        <h1 className="mt-1 text-2xl font-extrabold text-navy sm:text-3xl">Your dashboard</h1>
        <p className="mt-2 max-w-2xl text-navy/70">Your street is a shared story. Tell us what needs care, then follow every step until it is done.</p>
        <Link to="/app/report" className="mt-5 inline-block">
          <Button>
            <Plus size={16} /> Report an issue
          </Button>
        </Link>
      </Card>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-navy/60">My reports</p>
          <p className="text-3xl font-extrabold">{items.length}</p>
        </Card>
        <Card>
          <p className="text-sm text-navy/60">Open</p>
          <p className="text-3xl font-extrabold">{open.length}</p>
        </Card>
        <Card className="md:col-span-1">
          <p className="text-sm text-navy/60 dark:text-slate-400">Active report</p>
          <div className="mt-2">
            <ActiveReportCarousel items={open.length ? open : items} href={(id) => `/app/reports/${id}`} />
          </div>
        </Card>
      </div>
      {loading ? <Skeleton className="h-40" /> : items.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {items.slice(0, 4).map((item) => (
            <IncidentCard key={item.id} incident={item} to={`/app/reports/${item.id}`} />
          ))}
        </div>
      ) : (
        <EmptyState title="No reports yet" body="When you file your first issue, it will live here with a CIV reference." action={<Link to="/app/report"><Button>Start a report</Button></Link>} />
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3">
          <h2 className="text-xl font-bold">Nearby issues</h2>
          {nearby.length ? nearby.slice(0, 3).map((item) => (
            <IncidentCard key={item.id} incident={item} to={`/app/reports/${item.id}`} />
          )) : <p className="text-sm text-navy/60">Public reports in your service area will appear here.</p>}
        </Card>
        <Card className="space-y-3">
          <h2 className="text-xl font-bold">Saved places</h2>
          {places.map((place) => (
            <div key={String(place.id)} className="flex items-center justify-between rounded-2xl bg-foam px-3 py-2 text-sm">
              <span>{String(place.label)} · {String(place.radius_m || 800)}m</span>
              <Button variant="ghost" type="button" onClick={async () => { await endpoints.deleteLocation(String(place.id)); setPlaces((cur) => cur.filter((p) => p.id !== place.id)); }}>
                Remove
              </Button>
            </div>
          ))}
          <div className="flex flex-wrap gap-2">
            <Input value={placeLabel} onChange={(e) => setPlaceLabel(e.target.value)} className="max-w-[10rem]" />
            <Button
              type="button"
              variant="soft"
              onClick={async () => {
                if (!navigator.geolocation) {
                  toast("Location is not available in this browser", "err");
                  return;
                }
                navigator.geolocation.getCurrentPosition(async (pos) => {
                  try {
                    const saved = (await endpoints.saveLocation({
                      label: placeLabel,
                      lat: pos.coords.latitude,
                      lng: pos.coords.longitude,
                      radius_m: 800,
                    })) as { id: string };
                    setPlaces((cur) => [...cur, { ...saved, label: placeLabel, radius_m: 800 }]);
                    toast("Place saved");
                  } catch (err) {
                    toast(err instanceof Error ? err.message : "Could not save place", "err");
                  }
                }, () => toast("Location permission is needed to save this place", "err"));
              }}
            >
              Save current location
            </Button>
          </div>
          <p className="text-xs text-navy/50">We only use location after you choose to save it. There is no background tracking.</p>
        </Card>
      </div>
    </div>
  );
}

function ReportPhotoStrip({ files, label = "Attached photos" }: { files: File[]; label?: string }) {
  const urls = useFileObjectUrls(files);
  if (!files.length) return null;
  return (
    <div className="rounded-2xl border border-teal/25 bg-mint/20 p-3 dark:border-teal/30 dark:bg-teal/5">
      <p className="text-sm font-bold text-navy dark:text-white">
        {label} <span className="font-normal text-navy/60">({files.length})</span>
      </p>
      <ul className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {files.map((file, index) => (
          <li
            key={`${file.name}-${file.size}-${file.lastModified}`}
            className="overflow-hidden rounded-xl border-2 border-white bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900"
          >
            {urls[index] ? (
              <img src={urls[index]} alt={file.name} className="aspect-[4/3] w-full object-cover" />
            ) : (
              <div className="aspect-[4/3] animate-pulse bg-navy/10" />
            )}
            <p className="truncate px-2 py-1.5 text-[10px] font-medium text-navy/70">{file.name}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ReportPage() {
  const toast = useToast();
  const [step, setStep] = useState(1);
  const [categories, setCategories] = useState<Category[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [keepAttachmentsPrivate, setKeepAttachmentsPrivate] = useState(false);
  const [suggestion, setSuggestion] = useState<Record<string, unknown> | null>(null);
  const [classificationToken, setClassificationToken] = useState("");
  const [classifyFailed, setClassifyFailed] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [created, setCreated] = useState<Complaint | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<ReportValues>({
    resolver: zodResolver(reportSchema),
    defaultValues: { title: "", description: "", category_id: "", locality: "" },
  });
  const values = form.watch();

  useEffect(() => {
    endpoints.categories().then(setCategories).catch(() => undefined);
    endpoints.departments().then(setDepartments).catch(() => undefined);
  }, []);

  const selectedCategory = categories.find((c) => c.id === values.category_id);
  const selectedDept =
    departments.find((d) => d.id === selectedCategory?.department_id) ||
    (suggestion?.department_code
      ? departments.find((d) => d.code === String(suggestion.department_code))
      : undefined);

  async function suggest() {
    const current = form.getValues();
    if ((current.title || "").trim().length < 3 || (current.description || "").trim().length < 8) return;
    setClassifying(true);
    try {
      const res = await endpoints.classifyAttachments({
        title: current.title,
        description: current.description,
        locality: current.locality,
      }, files);
      setSuggestion(res);
      setClassificationToken(typeof res.classification_token === "string" ? res.classification_token : "");
      setClassifyFailed(res.ai_generated === false);
    } catch {
      setSuggestion(null);
      setClassificationToken("");
      setClassifyFailed(true);
    } finally {
      setClassifying(false);
    }
  }

  async function submit(data: ReportValues) {
    if (submitting) return;
    setSubmitting(true);
    try {
      const incident = await endpoints.createComplaintWithAttachments({
        ...data,
        photo_count: files.length,
        occurred_at: data.occurred_at ? new Date(data.occurred_at).toISOString() : undefined,
      }, files, keepAttachmentsPrivate, classificationToken || undefined);
      setCreated(incident);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not submit", "err");
    } finally {
      setSubmitting(false);
    }
  }

  if (created) {
    return (
      <Card className="mx-auto max-w-xl text-center">
        <p className="chip bg-mint text-navy">Submitted</p>
        <h1 className="mt-4 text-3xl font-extrabold">We heard you</h1>
        <p className="mt-2 text-navy/70">Keep this reference handy.</p>
        <p className="mt-4 font-mono text-2xl font-bold text-teal">{created.reference}</p>
        <Link to={`/app/reports/${created.id}`} className="mt-6 inline-block">
          <Button>Track this report</Button>
        </Link>
      </Card>
    );
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 px-1">
      <div className="rounded-3xl bg-coral/60 px-4 py-3 text-sm font-semibold text-navy dark:text-navy">
        For emergencies call 112. Civicon AI is for civic issues, not ambulance, fire or crime in progress.
      </div>
      <h1 className="text-3xl font-extrabold text-navy dark:text-white">Report an issue</h1>
      <ProgressTracker steps={REPORT_PROGRESS_STEPS} current={step} className="rounded-2xl bg-white/60 p-4 dark:bg-slate-900/40" />
      {step === 1 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {categories.map((cat) => {
            const Icon = categoryIcon(cat.icon || cat.slug);
            return (
              <button
                type="button"
                key={cat.id}
                onClick={() => {
                  form.setValue("category_id", cat.id, { shouldValidate: true });
                  const currentTitle = form.getValues("title").trim();
                  const previous = categories.find((c) => c.id === values.category_id);
                  if (!currentTitle || (previous && currentTitle === previous.name)) {
                    form.setValue("title", cat.name, { shouldDirty: true });
                  } else if (!currentTitle.toLowerCase().startsWith(cat.name.toLowerCase())) {
                    form.setValue("title", `${cat.name} — ${currentTitle}`.slice(0, 140), { shouldDirty: true });
                  }
                  setStep(2);
                }}
                className={cx(
                  "card flex min-h-[8.5rem] flex-col gap-2 p-4 text-left transition hover:ring-2 hover:ring-teal/40",
                  values.category_id === cat.id && "ring-2 ring-teal",
                )}
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-teal/15 text-teal">
                  <Icon size={20} aria-hidden />
                </span>
                <p className="font-bold text-navy dark:text-white">{cat.name}</p>
                <p className="line-clamp-2 text-sm text-navy/60 dark:text-slate-400">{cat.description}</p>
              </button>
            );
          })}
        </div>
      ) : null}
      {step === 2 ? (
        <Card className="space-y-4">
          {selectedCategory ? (
            <p className="flex items-center gap-2 text-sm font-semibold text-teal">
              <CategoryIconBadge slugOrIcon={selectedCategory.icon || selectedCategory.slug} className="h-8 w-8 rounded-lg bg-teal/15" size={16} />
              Issue: {selectedCategory.name}
            </p>
          ) : null}
          <Field label="Title" error={form.formState.errors.title?.message}>
            <Input {...form.register("title")} />
          </Field>
          <Field label="What did you notice?" error={form.formState.errors.description?.message}>
            <Textarea {...form.register("description")} />
          </Field>
          <Field label="When did this happen?">
            <Input type="datetime-local" {...form.register("occurred_at")} />
          </Field>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button
              type="button"
              onClick={async () => {
                const ok = await form.trigger(["title", "description"]);
                if (!ok) return;
                setStep(3);
                void suggest();
              }}
            >
              Continue
            </Button>
          </div>
        </Card>
      ) : null}
      {step === 3 ? (
        <Card className="space-y-4">
          {selectedCategory ? (
            <p className="text-sm font-semibold text-teal">Issue: {selectedCategory.name}</p>
          ) : null}
          <Field label="Locality" error={form.formState.errors.locality?.message}>
            <Input {...form.register("locality")} />
          </Field>
          <LocationPicker
            locality={values.locality}
            latitude={values.latitude}
            longitude={values.longitude}
            onBlocked={(msg) => toast(msg, "err")}
            onChange={(next) => {
              if (next.latitude != null) form.setValue("latitude", next.latitude);
              if (next.longitude != null) form.setValue("longitude", next.longitude);
              if (next.locality) form.setValue("locality", next.locality);
              if (next.address) form.setValue("address", next.address);
            }}
          />
          <p className="rounded-2xl bg-foam p-3 text-sm text-navy/75 dark:bg-slate-800 dark:text-slate-300">
            Civic issues are public. Visitors who are not signed in can see the issue and locality. Signed-in users can
            also see its status, brief summary, assigned officer name, and municipality.
          </p>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => setStep(2)}>
              Back
            </Button>
            <Button
              type="button"
              onClick={async () => {
                const ok = await form.trigger(["locality"]);
                if (ok) setStep(4);
              }}
            >
              Continue
            </Button>
          </div>
        </Card>
      ) : null}
      {step === 4 ? (
        <Card className="space-y-4">
          {selectedCategory ? (
            <p className="text-sm font-semibold text-teal">Issue: {selectedCategory.name}</p>
          ) : null}
          <FileUpload files={files} onChange={setFiles} max={4} />
          <ReportPhotoStrip files={files} label="Preview" />
          <div className="rounded-2xl bg-foam p-3 text-sm dark:bg-slate-800">
            <label className="flex items-start gap-2 font-semibold text-navy dark:text-white">
              <input
                type="checkbox"
                checked={keepAttachmentsPrivate}
                onChange={(event) => setKeepAttachmentsPrivate(event.target.checked)}
                className="mt-1"
              />
              Keep attachment private to officials
            </label>
            <p className="mt-1 pl-6 text-navy/70 dark:text-slate-300">
              Off by default: signed-in users can view the photos. When checked, only you and authorized municipal
              officials can view them. Gemini still analyzes attached photos to create the summary and image inference.
            </p>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => setStep(3)}>
              Back
            </Button>
            <Button
              type="button"
              disabled={classifying}
              onClick={async () => {
                await suggest();
                setStep(5);
              }}
            >
              {classifying ? "Analysing report and images…" : "Review"}
            </Button>
          </div>
        </Card>
      ) : null}
      {step === 5 ? (
        <Card className={cx("relative space-y-4", submitting && "opacity-95")}>
          {submitting ? (
            <p className="rounded-2xl bg-mint/60 px-3 py-2 text-sm font-semibold text-navy">Submitting your report…</p>
          ) : null}
          {selectedCategory ? (
            <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-teal">
              <CategoryIconBadge slugOrIcon={selectedCategory.icon || selectedCategory.slug} size={16} />
              Category: {selectedCategory.name}
              {selectedDept ? ` → ${selectedDept.name} (${selectedDept.code})` : ""}
            </p>
          ) : null}
          <h2 className="text-xl font-bold dark:text-white">{values.title}</h2>
          <p className="text-navy/70 dark:text-slate-300">{values.description}</p>
          {suggestion?.summary ? (
            <div className="rounded-2xl bg-mint/40 p-3 text-sm dark:bg-teal/10">
              <p className="font-semibold text-navy dark:text-white">AI summary</p>
              <p className="mt-1 text-navy/80 dark:text-slate-200">{String(suggestion.summary)}</p>
            </div>
          ) : null}
          {files.length && suggestion?.attachment_inference ? (
            <div className="rounded-2xl bg-sky/50 p-3 text-sm dark:bg-sky/10">
              <p className="font-semibold text-navy dark:text-white">Attached Documents inference</p>
              <p className="mt-1 text-navy/80 dark:text-slate-200">{String(suggestion.attachment_inference)}</p>
            </div>
          ) : null}
          <p className="text-sm dark:text-slate-300">{values.locality}</p>
          <ReportPhotoStrip files={files} />
          <div className="rounded-2xl bg-foam p-3 text-sm dark:bg-slate-800/80">
            <p className="font-semibold text-navy dark:text-white">How departments are assigned</p>
            <p className="mt-1 text-navy/70 dark:text-slate-300">
              Your chosen category is linked to a municipal department (for example PWD for roads, SAN for garbage). That department receives the report.
              Optional AI may suggest severity or a different department code — officers can override either at any time.
            </p>
            {selectedDept ? (
              <p className="mt-2 text-navy/80 dark:text-slate-200">
                Routing: <strong>{selectedDept.name}</strong> ({selectedDept.code})
                {selectedDept.description ? ` — ${selectedDept.description}` : ""}
              </p>
            ) : null}
          </div>
          {classifyFailed ? (
            <div className="rounded-2xl border border-amber-200/80 bg-amber-50/80 p-3 text-sm dark:border-amber-500/30 dark:bg-amber-950/30">
              <p className="font-semibold text-navy dark:text-white">AI summary unavailable</p>
              <p className="mt-1 text-navy/70 dark:text-slate-300">Your original description will be kept. Gemini will be retried when you submit.</p>
              <p className="mt-2 rounded-xl bg-white/80 p-2 text-navy/90 dark:bg-slate-900/60 dark:text-slate-200">{values.description}</p>
            </div>
          ) : null}
          {suggestion?.severity && !classifyFailed ? (
            <div className="rounded-2xl bg-foam p-3 text-sm dark:bg-slate-800">
              <p className="font-semibold text-navy dark:text-white">Suggested urgency for officers</p>
              <p className="mt-1">
                <SeverityBadge severity={String(suggestion.severity)} /> · Department {String(suggestion.department_code || selectedDept?.code || "—")}
              </p>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="ghost" onClick={() => setStep(4)} disabled={submitting}>
              Back
            </Button>
            <Button type="button" onClick={form.handleSubmit(submit)} disabled={submitting}>
              {submitting ? "Submitting…" : "Submit report"}
            </Button>
          </div>
        </Card>
      ) : null}
    </div>
  );
}

export function MyReportsPage() {
  const [items, setItems] = useState<Complaint[]>([]);
  const [q, setQ] = useState("");
  useEffect(() => {
    endpoints.complaints("?mine=true").then((res) => setItems(res.items)).catch(() => setItems([]));
  }, []);
  const filtered = items.filter((i) => !q || i.title.toLowerCase().includes(q.toLowerCase()) || i.reference.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-extrabold">My reports</h1>
      <Input placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-sm" />
      {filtered.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {filtered.map((item) => (
            <IncidentCard key={item.id} incident={item} to={`/app/reports/${item.id}`} />
          ))}
        </div>
      ) : (
        <EmptyState title="Nothing here yet" body="New reports appear with a CIV reference as soon as they are submitted." />
      )}
    </div>
  );
}

export function IncidentDetailPage({ base = "/app/reports" }: { base?: string }) {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const toast = useToast();
  const [item, setItem] = useState<Complaint | null>(null);
  const [note, setNote] = useState("");
  const [internal, setInternal] = useState(false);
  const [officers, setOfficers] = useState<User[]>([]);
  const [officerId, setOfficerId] = useState("");
  const [images, setImages] = useState<Record<string, string>>({});
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [promoted, setPromoted] = useState(false);
  const privileged = ["OFFICER", "ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3"].includes(user?.role || "");
  const isOwnerCitizen =
    user?.role === "CITIZEN" && (item?.reporter_id === user?.id || item?.reporter?.id === user?.id);
  const isPersonal = isOwnerCitizen || privileged;
  const showTimeline = isPersonal;
  const showOfficerTriage = Boolean(item?.ai_summary);

  async function load() {
    const doc = await endpoints.complaint(id);
    setItem(doc);
    setPromoted(Boolean(doc.viewer_has_promoted));
    const map: Record<string, string> = {};
    for (const att of doc.attachments || []) {
      try {
        map[att.id] = await fetchAttachmentBlob(att.id);
      } catch {
        /* skip */
      }
    }
    setImages(map);
  }

  useEffect(() => {
    load().catch((err: Error) => toast(err.message, "err"));
    if (privileged) endpoints.officers().then(setOfficers).catch(() => undefined);
  }, [id]);

  if (!item) return <Skeleton className="h-64" />;
  const next = item.status ? NEXT_STATUSES[item.status] || [] : [];

  async function confirmDeleteReport() {
    if (!item) return;
    setDeleteBusy(true);
    try {
      await endpoints.deleteComplaint(item.id);
      toast("Report deleted");
      window.location.assign("/app/reports");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not delete", "err");
      setDeleteBusy(false);
    }
  }

  const progress = (
    <ProgressTracker
      steps={INCIDENT_PROGRESS_STEPS}
      current={incidentProgressIndex(item.status)}
      orientation={privileged ? "vertical" : "horizontal"}
      className={
        privileged
          ? "rounded-xl border border-navy/8 bg-white/90 p-3 dark:border-white/10 dark:bg-slate-900/80 lg:sticky lg:top-20"
          : "rounded-2xl bg-white/70 p-4 dark:bg-slate-900/50 sm:p-5"
      }
    />
  );

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-10 sm:space-y-8">
      <ConfirmDialog
        open={deleteOpen}
        title="Delete this report?"
        description="This permanently removes your report, photos, and timeline. You cannot undo this action."
        confirmLabel="Delete report"
        cancelLabel="Keep report"
        busy={deleteBusy}
        onCancel={() => {
          if (!deleteBusy) setDeleteOpen(false);
        }}
        onConfirm={() => void confirmDeleteReport()}
      />
      {!privileged ? progress : null}

      <div className={cx(privileged ? "grid gap-4 lg:grid-cols-[minmax(0,1fr)_9.5rem] lg:gap-5 xl:grid-cols-[minmax(0,1fr)_10.5rem]" : "space-y-4 sm:space-y-6")}>
        <div className="min-w-0 space-y-4 sm:space-y-5">
        <Card className="relative space-y-3 p-4 sm:space-y-4 sm:p-5">
          {isOwnerCitizen ? (
            <button
              type="button"
              className="absolute right-4 top-4 rounded-full p-2.5 text-rose-600 transition hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40"
              aria-label="Delete report"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 size={20} aria-hidden />
            </button>
          ) : null}
          <div className="flex items-start gap-3">
            <CategoryIconBadge slugOrIcon={item.category?.icon || item.category?.slug} className="mt-1 h-11 w-11 rounded-2xl" size={22} />
            <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase text-teal">{item.reference}</p>
          <h1 className={cx("mt-1 text-xl font-extrabold sm:text-2xl", isOwnerCitizen && "pr-10")}>{item.title}</h1>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge status={item.status} />
            {item.severity ? <SeverityBadge severity={item.severity} /> : null}
            {item.priority?.label ? <span className="chip bg-sky text-navy">{item.priority.label} {item.priority.score}</span> : null}
          </div>
          <SlaTimer ack={item.sla?.ack_due} resolve={item.sla?.resolve_due} />
          {item.department?.name ? <p className="text-sm text-navy/60">Routed to {item.department.name}</p> : null}
          {item.assignee?.display_name ? (
            <p className="text-sm text-navy/70">Assigned officer: {item.assignee.display_name}</p>
          ) : null}
          {item.municipality_name ? (
            <p className="text-sm text-navy/70">Municipality: {item.municipality_name}</p>
          ) : null}
          {item.reporter?.phone ? (
            <p className="text-sm font-medium text-navy/80 dark:text-slate-200">
              Reporter: {item.reporter.display_name} · <a href={`tel:${item.reporter.phone}`} className="text-teal">{item.reporter.phone}</a>
            </p>
          ) : null}
          {item.assignee?.phone ? (
            <p className="text-sm font-medium text-navy/80 dark:text-slate-200">
              Assigned officer: {item.assignee.display_name} · <a href={`tel:${item.assignee.phone}`} className="text-teal">{item.assignee.phone}</a>
            </p>
          ) : null}
          <p className="text-base leading-relaxed text-navy/80 dark:text-slate-200">
            {isPersonal ? item.description : item.summary || item.description}
          </p>
          <p className="flex items-center gap-2 text-sm font-medium text-navy/70 dark:text-slate-300">
            <MapPin size={16} className="shrink-0 text-teal" aria-hidden /> {item.locality}
          </p>
          {showOfficerTriage ? (
            <div className="rounded-2xl bg-foam p-4 text-sm dark:bg-slate-800">
              <p className="font-semibold">AI summary and classification</p>
              {item.ai_summary ? <p className="mt-2 text-navy/80 dark:text-slate-200">{item.ai_summary}</p> : null}
              <p className="mt-2 flex flex-wrap items-center gap-2">
                {item.ai_category_slug ? <span>Category: {item.ai_category_slug}</span> : null}
                {item.ai_severity ? <span>· Severity: {item.ai_severity}</span> : null}
                {item.ai_department_code ? <span>· Department: {item.ai_department_code}</span> : null}
              </p>
              {item.ai_rationale && item.ai_rationale !== "No Summary" ? (
                <p className="mt-2 text-navy/70">Reason: {item.ai_rationale}</p>
              ) : null}
              {item.attachment_inference ? (
                <p className="mt-2 text-navy/80 dark:text-slate-200">
                  <strong>Attached Documents inference:</strong> {item.attachment_inference}
                </p>
              ) : null}
              {privileged ? <p className="mt-2 text-xs text-navy/50">Review the attachments below. Override status or assignment anytime.</p> : null}
            </div>
          ) : null}
          {isOwnerCitizen && item.similar?.length ? (
            <p className="text-sm text-navy/60">Similar open reports: {item.similar.map((s) => s.reference).join(", ")}</p>
          ) : null}
          {user?.role === "CITIZEN" && !isOwnerCitizen ? (
            <div className="flex flex-wrap gap-3 pt-2">
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
                    toast(err instanceof Error ? err.message : "Could not promote", "err");
                  }
                }}
              />
              {item.source === "auto_weather" ? (
                <Button type="button" variant="ghost" onClick={async () => { try { await endpoints.better(item.id); toast("Marked currently better"); await load(); } catch (err) { toast(err instanceof Error ? err.message : "Could not vote", "err"); } }}>
                  Currently better
                </Button>
              ) : null}
            </div>
          ) : null}
          {isOwnerCitizen && (item.status === "RESOLVED" || item.status === "resolved_pending_verification") ? (
            <div className="flex flex-wrap gap-3 pt-2">
              <Button type="button" onClick={async () => { try { await endpoints.verify(item.id, "resolved"); toast("Thanks — marked complete", "ok"); await load(); } catch (err) { toast(err instanceof Error ? err.message : "Could not verify", "err"); } }}>
                Yes, it's fixed
              </Button>
              <Button type="button" variant="danger" onClick={async () => { try { await endpoints.verify(item.id, "unresolved"); toast("Still a problem"); await load(); } catch (err) { toast(err instanceof Error ? err.message : "Could not verify", "err"); } }}>
                Still a problem
              </Button>
            </div>
          ) : null}
        </Card>
        <Card className="space-y-3 p-4 sm:p-5">
          <h2 className="text-base font-bold sm:text-lg">Photos & evidence</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {(item.attachments || []).length ? (
              (item.attachments || []).map((att) =>
                images[att.id] ? (
                  <div key={att.id}>
                    <img src={images[att.id]} alt={att.original_name || "Issue attachment"} className="max-h-56 w-full rounded-2xl object-cover" />
                    {att.is_private ? <p className="mt-1 text-xs text-navy/60">Private to you and authorized officials</p> : null}
                  </div>
                ) : (
                  <Skeleton key={att.id} className="h-40" />
                ),
              )
            ) : (
              <p className="text-sm text-navy/60">No images uploaded.</p>
            )}
          </div>
        </Card>
        <Card className="space-y-3 p-4 sm:p-5">
          <h2 className="text-base font-bold sm:text-lg">Conversation</h2>
          <div className="space-y-3">
            {(item.comments || []).map((c) => (
              <div key={c.id} className={cx("rounded-2xl p-3 text-sm", c.is_internal ? "bg-peach/50" : "bg-foam")}>
                {c.is_internal ? <p className="text-xs font-bold">Internal</p> : null}
                <p className="font-semibold text-navy dark:text-white">{c.author?.display_name || "Community member"}</p>
                <p className="mt-1 text-navy/80 dark:text-slate-200">{c.body}</p>
                <p className="mt-1 text-xs text-navy/50">{formatDate(c.created_at)}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 space-y-2">
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a note" />
            {privileged ? (
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} /> Internal note
              </label>
            ) : null}
            <Button
              type="button"
              onClick={async () => {
                try {
                  await endpoints.comment(item.id, { body: note, is_internal: internal });
                  setNote("");
                  await load();
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Could not comment", "err");
                }
              }}
            >
              Post note
            </Button>
          </div>
        </Card>
        {showTimeline ? (
          <Card className="space-y-4 p-6">
            <h2 className="text-lg font-bold">Timeline</h2>
            <Timeline history={item.history} />
          </Card>
        ) : null}
        {privileged ? (
          <Card className="space-y-3 p-4 sm:p-5">
            <h2 className="text-base font-bold">Officer actions</h2>
            <Button type="button" variant="soft" onClick={async () => { try { await endpoints.claim(item.id); toast("Claimed"); await load(); } catch (err) { toast(err instanceof Error ? err.message : "Could not claim", "err"); } }}>
              Claim / add to my board
            </Button>
            <div className="flex flex-wrap gap-2">
              {next.map((status) => (
                <Button
                  key={status}
                  variant="soft"
                  type="button"
                  onClick={async () => {
                    try {
                      await endpoints.status(item.id, { status, note: note || undefined });
                      toast("Status updated");
                      await load();
                    } catch (err) {
                      toast(err instanceof Error ? err.message : "Update failed", "err");
                    }
                  }}
                >
                  {status.replaceAll("_", " ")}
                </Button>
              ))}
            </div>
            <select className="w-full rounded-2xl border px-3 py-2 text-sm" value={officerId} onChange={(e) => setOfficerId(e.target.value)}>
              <option value="">Assign officer</option>
              {officers.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.display_name}
                </option>
              ))}
            </select>
            <Button
              type="button"
              variant="ghost"
              onClick={async () => {
                if (!officerId) return;
                await endpoints.assign(item.id, { officer_id: officerId });
                toast("Assigned");
                await load();
              }}
            >
              Assign
            </Button>
            <FileAttachButton
              label="Add evidence photo"
              onFile={async (file) => {
                await endpoints.attach(item.id, file, "evidence");
                toast("Evidence uploaded");
                await load();
              }}
            />
            <Button
              type="button"
              variant="danger"
              onClick={async () => {
                const reason = window.prompt("Why escalate this incident?");
                if (!reason || reason.length < 8) return;
                try {
                  await endpoints.escalate(item.id, reason);
                  toast("Escalated");
                  await load();
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Escalation failed", "err");
                }
              }}
            >
              Escalate
            </Button>
          </Card>
        ) : null}
      <Link to={base} className="inline-block text-sm font-semibold text-teal">
        Back to list
      </Link>
        </div>
        {privileged ? (
          <aside className="hidden lg:block">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-navy/45">Progress</p>
            {progress}
          </aside>
        ) : null}
        {privileged ? <div className="lg:hidden">{progress}</div> : null}
      </div>
    </div>
  );
}

export function NotificationsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState(notificationTabs(user?.role)[0]);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [quiet, setQuiet] = useState("23:00");
  const tabs = notificationTabs(user?.role);
  async function load() {
    const res = await endpoints.v1Notifications(tab);
    setItems(res.items);
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, [tab]);
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-extrabold">Notifications</h1>
        <Button variant="ghost" onClick={async () => { await endpoints.readAll(); await load(); }}>
          Mark all read
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {tabs.map((name) => (
          <Button key={name} variant={tab === name ? "primary" : "ghost"} onClick={() => setTab(name)}>
            {name.replace("_", " ")}
          </Button>
        ))}
      </div>
      <Card className="flex flex-wrap items-end gap-3">
        <Field label="Quiet hours start">
          <Input value={quiet} onChange={(e) => setQuiet(e.target.value)} />
        </Field>
        <Button type="button" variant="soft" onClick={async () => { await endpoints.savePrefs({ quiet_hours: { start: quiet, end: "06:00" }, push_min_priority: "High" }); }}>
          Save preferences
        </Button>
        <p className="text-xs text-navy/50">Live updates use authenticated polling. Firestore is not used.</p>
      </Card>
      {items.length ? (
        items.map((item) => (
          <Card key={item.id} className={cx("flex items-start gap-3", !item.read_at && "ring-1 ring-teal/40")}>
            <Bell size={16} className="mt-1 text-teal" />
            <div className="flex-1">
              <p className="font-bold">{item.title}</p>
              <p className="text-sm text-navy/70">{item.body}</p>
              <p className="text-xs text-navy/50">{formatDate(item.created_at)}</p>
              {item.incident_id ? (
                <Link className="text-xs font-semibold text-teal" to={`/app/reports/${item.incident_id}`}>
                  Open incident
                </Link>
              ) : null}
            </div>
            {!item.read_at ? (
              <Button variant="ghost" onClick={async () => { await endpoints.readNotification(item.id); await load(); }}>
                Read
              </Button>
            ) : null}
          </Card>
        ))
      ) : (
        <EmptyState title="You're all caught up" body="Updates about assignments, status changes and escalations will land here." />
      )}
    </div>
  );
}

export function ProfilePage() {
  const { user, refreshMe, logout } = useAuth();
  const toast = useToast();
  const [name, setName] = useState(user?.display_name || "");
  const [locality, setLocality] = useState(user?.locality || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [dob, setDob] = useState(user?.date_of_birth || "");
  const [localities, setLocalities] = useState<Array<{ id: string; name: string }>>([]);
  const [savedSnapshot, setSavedSnapshot] = useState("");
  const [saving, setSaving] = useState(false);

  const snapshot = JSON.stringify({ name, locality, phone, dob });
  const dirty = snapshot !== savedSnapshot;

  useEffect(() => {
    endpoints.localities().then(setLocalities).catch(() => undefined);
  }, []);

  useEffect(() => {
    const next = {
      name: user?.display_name || "",
      locality: user?.locality || "",
      phone: user?.phone || "",
      dob: user?.date_of_birth || "",
    };
    setName(next.name);
    setLocality(next.locality);
    setPhone(next.phone);
    setDob(next.dob);
    setSavedSnapshot(JSON.stringify(next));
  }, [user]);

  return (
    <Card className="mx-auto max-w-xl space-y-4">
      <h1 className="text-3xl font-extrabold dark:text-white">My account</h1>
      <p className="text-sm text-navy/60 dark:text-slate-400">{user?.email} · {user?.role}</p>
      {!locality.trim() ? (
        <p className="rounded-2xl bg-peach/40 px-3 py-2 text-sm font-medium text-navy">Choose your locality so we can route reports correctly.</p>
      ) : null}
      {!(phone || "").trim() ? (
        <p className="rounded-2xl bg-coral/40 px-3 py-2 text-sm font-medium text-navy">Add your mobile number so officers and citizens can reach you when needed.</p>
      ) : null}
      <Field label="Display name">
        <Input value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label="Locality">
        <select
          className="w-full rounded-2xl border border-navy/10 bg-white px-4 py-2.5 text-sm text-navy dark:border-white/10 dark:bg-slate-900 dark:text-white"
          value={locality}
          onChange={(e) => setLocality(e.target.value)}
        >
          <option value="">Select your area</option>
          {localities.map((loc) => (
            <option key={loc.id} value={loc.name}>
              {loc.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Mobile number">
        <Input value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" autoComplete="tel" required minLength={8} />
      </Field>
      <Field label="Date of birth (optional)">
        <Input value={dob} onChange={(e) => setDob(e.target.value)} type="date" />
      </Field>
      <Button
        type="button"
        disabled={!dirty || saving || (phone || "").trim().length < 8}
        onClick={async () => {
          if ((phone || "").trim().length < 8) {
            toast("Add a valid mobile number (at least 8 digits)", "err");
            return;
          }
          setSaving(true);
          try {
            await endpoints.profile({
              display_name: name,
              locality: locality || undefined,
              phone: phone.trim(),
              date_of_birth: dob || undefined,
            });
            await refreshMe();
            setSavedSnapshot(snapshot);
            toast("Profile saved", "ok");
          } catch (err) {
            toast(err instanceof Error ? err.message : "Could not save", "err");
          } finally {
            setSaving(false);
          }
        }}
      >
        {saving ? "Saving…" : dirty ? "Save changes" : "Saved"}
      </Button>
      <Button variant="ghost" type="button" onClick={logout}>
        Sign out
      </Button>
    </Card>
  );
}

export function OfficerHome() {
  return <L1Board />;
}
