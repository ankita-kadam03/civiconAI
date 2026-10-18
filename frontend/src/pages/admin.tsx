import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { IncidentCard } from "../components/incidents";
import { IncidentMap } from "../components/maps";
import { Button, Card, Field, Input, Skeleton } from "../components/ui";
import { endpoints } from "../lib/api";
import { cx } from "../lib/format";
import { useToast } from "../lib/toast";
import type { Analytics, Category, Complaint, Department, Role, User } from "../lib/types";

const COLORS = ["#2A9D8F", "#E8E4FF", "#FFB4A2", "#D7EEFF", "#F4D35E", "#1B2545"];

const ADMIN_LINKS = [
  ["Overview", "/admin"],
  ["Incidents", "/admin/incidents"],
  ["People", "/admin/users"],
  ["Categories", "/admin/categories"],
  ["Departments", "/admin/departments"],
  ["Rules", "/admin/rules"],
  ["Analytics", "/admin/analytics"],
  ["Audit", "/admin/audit"],
  ["Health", "/admin/integrations"],
];

function AdminNav() {
  const location = useLocation();
  return (
    <div className="mb-6 flex flex-wrap gap-2">
      {ADMIN_LINKS.map(([label, href]) => (
        <Link
          key={href}
          to={href}
          className={cx(
            "rounded-full px-3 py-1.5 text-sm font-semibold",
            location.pathname === href ? "bg-navy text-white" : "bg-white text-navy/70",
          )}
        >
          {label}
        </Link>
      ))}
    </div>
  );
}

export function AdminHome() {
  const [stats, setStats] = useState<Analytics | null>(null);
  const [incidents, setIncidents] = useState<Complaint[]>([]);
  useEffect(() => {
    endpoints.analytics().then(setStats).catch(() => undefined);
    endpoints.complaints("?page_size=8").then((res) => setIncidents(res.items)).catch(() => undefined);
  }, []);
  if (!stats) return <Skeleton className="h-64" />;
  const statusData = Object.entries(stats.by_status).map(([name, value]) => ({ name, value }));
  const catData = Object.entries(stats.by_category).map(([name, value]) => ({ name, value }));
  return (
    <div className="space-y-6">
      <AdminNav />
      <Card className="bg-gradient-to-r from-lavender via-white to-sky">
        <h1 className="text-3xl font-extrabold">Operations</h1>
        <p className="mt-2 text-navy/70">
          A live picture of neighbourhood reports.
          {stats.in_memory_data || stats.demo ? " Data is in-memory until Firestore is connected." : " These numbers come from live records."}
        </p>
      </Card>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Total", stats.total],
          ["Active", stats.active],
          ["Resolved", stats.resolved],
          ["Overdue", stats.overdue],
        ].map(([label, value]) => (
          <Card key={String(label)}>
            <p className="text-sm text-navy/60">{label}</p>
            <p className="text-3xl font-extrabold">{value}</p>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="h-80">
          <h2 className="mb-3 font-bold">By status</h2>
          <ResponsiveContainer>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>
                {statusData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card className="h-80">
          <h2 className="mb-3 font-bold">By category</h2>
          <ResponsiveContainer>
            <BarChart data={catData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" hide />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#2A9D8F" radius={8} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
      {stats.department_performance?.length ? (
        <Card className="h-80">
          <h2 className="mb-3 font-bold">Department load</h2>
          <ResponsiveContainer>
            <BarChart data={stats.department_performance.map((row) => ({ name: row.department, open: row.open, total: row.total }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" hide />
              <YAxis />
              <Tooltip />
              <Bar dataKey="open" fill="#2A9D8F" radius={8} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      ) : null}
      {stats.hotspots?.length ? (
        <Card>
          <h2 className="mb-3 font-bold">Recurrence hotspots (Firestore)</h2>
          <div className="space-y-2">
            {stats.hotspots.map((row) => (
              <div key={row.locality} className="flex items-center justify-between rounded-2xl bg-foam px-3 py-2 text-sm">
                <span>{row.locality}</span>
                <span className="font-bold">{row.count}</span>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
      {stats.bigquery?.enabled ? (
        <Card className="space-y-3">
          <h2 className="font-bold">BigQuery analytics (60-day recurrence)</h2>
          {stats.ai_platform ? <p className="text-sm text-navy/60">{stats.ai_platform}</p> : null}
          {stats.bigquery.summary ? (
            <p className="text-sm text-navy/70">
              Warehouse: {stats.bigquery.summary.total ?? 0} incidents · {stats.bigquery.summary.open ?? 0} open ·{" "}
              {stats.bigquery.summary.last_7_days ?? 0} in last 7 days
            </p>
          ) : null}
          {stats.bigquery.recurrence_60d?.length ? (
            <div className="space-y-2">
              {stats.bigquery.recurrence_60d.map((row) => (
                <div key={`${row.locality}-${row.category}`} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-lavender/40 px-3 py-2 text-sm">
                  <span>
                    {row.locality} · {row.category}
                  </span>
                  <span className="font-bold">{row.count} similar reports</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-navy/60">No recurring locality+category pairs yet (needs 2+ in 60 days).</p>
          )}
        </Card>
      ) : null}
      <IncidentMap incidents={incidents} />
      <div className="grid gap-4 md:grid-cols-2">
        {incidents.map((item) => (
          <IncidentCard key={item.id} incident={item} to={`/admin/incidents/${item.id}`} />
        ))}
      </div>
    </div>
  );
}

export function AdminIncidents() {
  const [items, setItems] = useState<Complaint[]>([]);
  useEffect(() => {
    endpoints.complaints("?page_size=50").then((res) => setItems(res.items)).catch(() => undefined);
  }, []);
  return (
    <div className="space-y-4">
      <AdminNav />
      <h1 className="text-3xl font-extrabold">Incident management</h1>
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <IncidentCard key={item.id} incident={item} to={`/admin/incidents/${item.id}`} />
        ))}
      </div>
    </div>
  );
}

export function UsersPage() {
  const toast = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  useEffect(() => {
    endpoints.users().then(setUsers).catch(() => undefined);
    endpoints.adminDepartments().then(setDepartments).catch(() => undefined);
  }, []);
  return (
    <div className="space-y-4">
      <AdminNav />
      <h1 className="text-3xl font-extrabold">People & roles</h1>
      {users.map((u) => (
        <Card key={u.id} className="flex flex-wrap items-center gap-3">
          <div className="flex-1">
            <p className="font-bold">{u.display_name}</p>
            <p className="text-sm text-navy/60">{u.email}</p>
          </div>
          <select
            className="rounded-2xl border px-3 py-2 text-sm"
            value={u.role}
            onChange={async (e) => {
              try {
                const next = await endpoints.patchUser(u.id, { role: e.target.value as Role, department_id: u.department_id });
                setUsers((prev) => prev.map((p) => (p.id === u.id ? next : p)));
              } catch (err) {
                toast(err instanceof Error ? err.message : "Could not change role", "err");
              }
            }}
          >
            {["CITIZEN", "OFFICER", "ADMIN"].map((role) => (
              <option key={role}>{role}</option>
            ))}
          </select>
          <select
            className="rounded-2xl border px-3 py-2 text-sm"
            value={u.department_id || ""}
            onChange={async (e) => {
              const next = await endpoints.patchUser(u.id, { role: u.role, department_id: e.target.value || null });
              setUsers((prev) => prev.map((p) => (p.id === u.id ? next : p)));
            }}
          >
            <option value="">No department</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </Card>
      ))}
    </div>
  );
}

export function CategoriesPage() {
  const toast = useToast();
  const [items, setItems] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  useEffect(() => {
    endpoints.adminCategories().then(setItems).catch(() => undefined);
  }, []);
  return (
    <div className="space-y-4">
      <AdminNav />
      <h1 className="text-3xl font-extrabold">Categories</h1>
      <Card className="grid gap-3 md:grid-cols-3">
        <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Slug"><Input value={slug} onChange={(e) => setSlug(e.target.value)} /></Field>
        <Button
          className="self-end"
          onClick={async () => {
            try {
              await endpoints.createCategory({ name, slug, icon: "map-pin" });
              setItems(await endpoints.adminCategories());
              toast("Category added");
            } catch (err) {
              toast(err instanceof Error ? err.message : "Failed", "err");
            }
          }}
        >
          Add
        </Button>
      </Card>
      {items.map((c) => (
        <Card key={c.id}>
          <p className="font-bold">{c.name}</p>
          <p className="text-sm text-navy/60">{c.slug}</p>
        </Card>
      ))}
    </div>
  );
}

export function DepartmentsPage() {
  const toast = useToast();
  const [items, setItems] = useState<Department[]>([]);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  useEffect(() => {
    endpoints.adminDepartments().then(setItems).catch(() => undefined);
  }, []);
  return (
    <div className="space-y-4">
      <AdminNav />
      <h1 className="text-3xl font-extrabold">Departments</h1>
      <Card className="grid gap-3 md:grid-cols-3">
        <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Code"><Input value={code} onChange={(e) => setCode(e.target.value)} /></Field>
        <Button
          className="self-end"
          onClick={async () => {
            try {
              await endpoints.createDepartment({ name, code });
              setItems(await endpoints.adminDepartments());
            } catch (err) {
              toast(err instanceof Error ? err.message : "Failed", "err");
            }
          }}
        >
          Add
        </Button>
      </Card>
      {items.map((d) => (
        <Card key={d.id}>
          <p className="font-bold">{d.name}</p>
          <p className="text-sm text-navy/60">{d.code}</p>
        </Card>
      ))}
    </div>
  );
}

export function RulesPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  useEffect(() => {
    endpoints.rules().then(setItems).catch(() => undefined);
  }, []);
  return (
    <div className="space-y-4">
      <AdminNav />
      <h1 className="text-3xl font-extrabold">Escalation rules</h1>
      {items.map((rule) => (
        <Card key={String(rule.id)}>
          <p className="font-bold">Level {String(rule.level)} · {String(rule.reason)}</p>
          <p className="text-sm text-navy/60">Review {String(rule.review_hours)}h · Resolve {String(rule.resolve_hours)}h</p>
        </Card>
      ))}
    </div>
  );
}

export function AnalyticsPage() {
  return <AdminHome />;
}

export function AuditPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  useEffect(() => {
    endpoints.audit().then((res) => setItems(res.items)).catch(() => undefined);
  }, []);
  return (
    <div className="space-y-3">
      <AdminNav />
      <h1 className="text-3xl font-extrabold">Audit log</h1>
      {items.map((row) => (
        <Card key={String(row.id)} className="text-sm">
          <p className="font-bold">{String(row.action)}</p>
          <p className="text-navy/60">{String(row.entity_type)} · {String(row.created_at)}</p>
        </Card>
      ))}
    </div>
  );
}

export function IntegrationsPage() {
  const [data, setData] = useState<Record<string, Record<string, unknown>> | null>(null);
  useEffect(() => {
    endpoints.integrations().then(setData).catch(() => undefined);
  }, []);
  if (!data) return <Skeleton className="h-40" />;
  return (
    <div className="space-y-4">
      <AdminNav />
      <h1 className="text-3xl font-extrabold">Integration health</h1>
      <Card className="space-y-2 bg-foam/80 text-sm text-navy/80 dark:bg-slate-800/80 dark:text-slate-200">
        <p className="font-bold text-navy dark:text-white">What Civicon uses (heads-up)</p>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>Firebase / Firestore</strong> — primary database (required).</li>
          <li><strong>Google Cloud Storage</strong> — report photo storage (required for uploads).</li>
          <li><strong>Vertex AI / Gemini</strong> — <strong>required</strong> for report classification (`GEMINI_API_KEY` or Vertex ADC).</li>
          <li><strong>BigQuery</strong> — <strong>required</strong> analytics warehouse (`BIGQUERY_DATASET`); incidents sync on create/update.</li>
          <li><strong>Google Maps</strong> — browser maps (frontend API key).</li>
        </ul>
      </Card>
      <p className="text-sm text-navy/60">Statuses never include secrets, keys or connection strings.</p>
      {Object.entries(data).map(([name, info]) => (
        <Card key={name}>
          <p className="font-bold capitalize">{name}</p>
          <pre className="mt-2 overflow-auto text-xs text-navy/70">{JSON.stringify(info, null, 2)}</pre>
        </Card>
      ))}
    </div>
  );
}
