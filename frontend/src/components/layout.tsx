import { Bell, CircleHelp, Compass, FileText, Info, Leaf, Menu, Moon, Phone, Shield, Sun, Workflow, X } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate, type To } from "react-router-dom";
import { landingNavSections } from "../pages/public";
import { notificationTabs, roleHome } from "../features/auth/paths";
import { useAuth } from "../lib/auth";
import { cx } from "../lib/format";
import { WeatherAlertBar } from "../features/weather/WeatherAlertBar";
import { CiviChat } from "./chat";
import { endpoints } from "../lib/api";
import { initPwaInstallListener, isStandalonePwa, promptPwaInstall } from "../lib/pwa-install";
import { useToast } from "../lib/toast";
import { Button } from "./ui";
import type { Role } from "../lib/types";

function landingLink(hash: string): To {
  return { pathname: "/", hash: `#${hash}` };
}

function isLandingSectionActive(pathname: string, hash: string, section: string) {
  return pathname === "/" && hash === `#${section}`;
}

const footerSectionIcons: Record<(typeof landingNavSections)[number]["hash"], typeof Compass> = {
  explore: Compass,
  "how-it-works": Workflow,
  about: Info,
  help: CircleHelp,
};

function FooterLink({ to, icon: Icon, children }: { to: To; icon: typeof Compass; children: ReactNode }) {
  return (
    <Link to={to} className="inline-flex items-center gap-2 rounded-lg py-1 transition hover:text-teal dark:hover:text-teal">
      <Icon size={16} className="shrink-0 opacity-70" aria-hidden />
      <span>{children}</span>
    </Link>
  );
}

export function Shell() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  const [unread, setUnread] = useState(0);
  const [pwaReady, setPwaReady] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!user) return;
    const load = () =>
      endpoints
        .v1Notifications(notificationTabs(user.role)[0])
        .then((res) => setUnread(res.unread || 0))
        .catch(() => undefined);
    void load();
    const id = window.setInterval(() => {
      void load();
    }, 20000);
    return () => window.clearInterval(id);
  }, [user, location.pathname]);

  useEffect(() => {
    if (isStandalonePwa()) return;
    return initPwaInstallListener(() => setPwaReady(true));
  }, []);

  useEffect(() => {
    if (!pwaReady || isStandalonePwa()) return;
    if (sessionStorage.getItem("civicon_pwa_hint") === "1") return;
    sessionStorage.setItem("civicon_pwa_hint", "1");
    toast("Install Civicon on your device for quick access from your home screen.", "info", { install: true });
  }, [pwaReady, toast]);

  const nav = useMemo(() => {
    if (!user) return null;
    const home = roleHome(user.role);
    const homeLabel = home === "/officer" ? "L1 board" : home === "/l2" ? "L2 board" : home === "/admin" ? "Admin" : "Home";
    const items: Array<[string, string]> = [[homeLabel, home]];
    if (user.role === "CITIZEN" || user.role === "ADMIN") items.push(["Report", "/app/report"], ["My reports", "/app/reports"]);
    if ((user.role === "ADMIN" || user.role === "ADMIN_L2" || user.role === "ADMIN_L3") && home !== "/officer") items.push(["L1 board", "/officer"]);
    if ((user.role === "ADMIN" || user.role === "ADMIN_L3") && home !== "/l2") items.push(["L2 board", "/l2"]);
    if (user.role === "ADMIN" || user.role === "ADMIN_L3") {
      if (home !== "/admin") items.push(["Admin", "/admin"]);
      items.push(["L3", "/l3"], ["People", "/admin/users"], ["Health", "/admin/integrations"]);
    }
    items.push(["Explore", "/explore"]);
    return items;
  }, [user]);

  function toggleDark() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-white/60 bg-white/70 backdrop-blur-md dark:border-white/10 dark:bg-slate-950/70">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-3 py-2.5 sm:px-4 sm:py-3">
          <Link to="/" className="flex min-w-0 items-center gap-2 font-extrabold text-navy dark:text-white">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-teal text-white">
              <Leaf size={18} />
            </span>
            <span className="truncate text-sm sm:text-base">Civicon AI</span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {!user
              ? landingNavSections.map(({ label, hash }) => (
                  <Link
                    key={hash}
                    to={landingLink(hash)}
                    onClick={() => {
                      if (location.pathname === "/") {
                        document.getElementById(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
                      }
                    }}
                    className={cx(
                      "rounded-full px-3 py-2 text-sm font-semibold",
                      isLandingSectionActive(location.pathname, location.hash, hash)
                        ? "bg-mint text-navy dark:bg-teal/20 dark:text-white"
                        : "text-navy/70 hover:bg-white dark:text-slate-200 dark:hover:bg-slate-800",
                    )}
                  >
                    {label}
                  </Link>
                ))
              : nav!.map(([label, href]) => (
                  <NavLink
                    key={href}
                    to={href}
                    end
                    className={({ isActive }) =>
                      cx(
                        "rounded-full px-3 py-2 text-sm font-semibold",
                        isActive ? "bg-mint text-navy dark:bg-teal/20 dark:text-white" : "text-navy/70 hover:bg-white dark:text-slate-200 dark:hover:bg-slate-800",
                      )
                    }
                  >
                    {label}
                  </NavLink>
                ))}
          </nav>
          <div className="flex items-center gap-2">
            {user ? (
              <Link
                to="/app/notifications"
                className="relative rounded-full p-2 text-navy hover:bg-white dark:text-slate-100 dark:hover:bg-slate-800"
                aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
              >
                <Bell size={18} />
                {unread ? <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-coral" /> : null}
              </Link>
            ) : null}
            {pwaReady && !isStandalonePwa() ? (
              <Button
                type="button"
                variant="soft"
                className="hidden px-3 py-1.5 text-xs md:inline-flex"
                onClick={() => void promptPwaInstall().then((ok) => !ok && toast("Use your browser menu: Install app / Add to Home screen.", "info"))}
              >
                Install app
              </Button>
            ) : null}
            <button
              type="button"
              className="rounded-full p-2 text-navy hover:bg-white dark:text-amber-300 dark:hover:bg-slate-800"
              onClick={toggleDark}
              aria-label="Toggle theme"
            >
              {dark ? <Sun size={18} className="text-amber-300" /> : <Moon size={18} />}
            </button>
            {user ? (
              <Link to="/app/profile" className="hidden rounded-full bg-lavender px-3 py-1.5 text-sm font-semibold md:inline">
                My account
              </Link>
            ) : (
              <Link to="/login">
                <Button>Sign in</Button>
              </Link>
            )}
            {user ? (
              <Button variant="ghost" className="hidden md:inline-flex" onClick={logout}>
                Sign out
              </Button>
            ) : null}
            <button type="button" className="rounded-full p-2 md:hidden" onClick={() => setOpen((v) => !v)} aria-label="Menu">
              {open ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
        {open ? (
          <div className="space-y-1 border-t border-navy/5 px-4 py-3 md:hidden">
            {!user
              ? landingNavSections.map(({ label, hash }) => (
                  <Link key={hash} to={landingLink(hash)} className="block rounded-2xl px-3 py-2 text-sm font-semibold hover:bg-white dark:hover:bg-slate-800">
                    {label}
                  </Link>
                ))
              : nav!.map(([label, href]) => (
                  <Link key={href} to={href} className="block rounded-2xl px-3 py-2 text-sm font-semibold hover:bg-white dark:hover:bg-slate-800">
                    {label}
                  </Link>
                ))}
            {user ? (
              <>
                <Link to="/app/profile" className="block rounded-2xl px-3 py-2 text-sm font-semibold hover:bg-white dark:hover:bg-slate-800 md:hidden">
                  My account
                </Link>
                <Link to="/app/notifications" className="block rounded-2xl px-3 py-2 text-sm font-semibold hover:bg-white dark:hover:bg-slate-800 md:hidden">
                  Notifications{unread ? ` (${unread})` : ""}
                </Link>
                <button type="button" className="block w-full rounded-2xl px-3 py-2 text-left text-sm font-semibold" onClick={logout}>
                  Sign out
                </button>
              </>
            ) : (
              <Link to="/login" className="block rounded-2xl px-3 py-2 text-sm font-semibold hover:bg-white dark:hover:bg-slate-800">
                Sign in
              </Link>
            )}
          </div>
        ) : null}
      </header>
      <WeatherAlertBar />
      <main className="mx-auto min-w-0 max-w-6xl px-3 py-5 sm:px-4 sm:py-8">
        <Outlet />
      </main>
      <footer className="mt-12 border-t border-navy/10 bg-foam/40 py-10 text-sm text-navy/65 dark:border-white/10 dark:bg-slate-900/40 dark:text-slate-400">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-8 px-4 md:grid-cols-3 md:items-start md:gap-x-10 md:gap-y-8">
          <div className="flex flex-col gap-3">
            <p className="inline-flex items-center gap-2 font-bold text-navy dark:text-white">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-teal text-white">
                <Leaf size={16} aria-hidden />
              </span>
              Civicon AI
            </p>
            <p className="max-w-xs leading-relaxed">Your Neighbourhood. Your Voice. Civic reporting with community-verified close.</p>
          </div>
          <div className="flex flex-col gap-2">
            <p className="mb-1 text-xs font-bold uppercase tracking-wide text-navy/45 dark:text-slate-500">Site</p>
            {landingNavSections.map(({ label, hash }) => (
              <FooterLink key={hash} to={landingLink(hash)} icon={footerSectionIcons[hash]}>
                {label}
              </FooterLink>
            ))}
          </div>
          <div className="flex flex-col gap-2">
            <p className="mb-1 text-xs font-bold uppercase tracking-wide text-navy/45 dark:text-slate-500">Legal</p>
            <FooterLink to="/privacy" icon={Shield}>
              Privacy
            </FooterLink>
            <FooterLink to="/terms" icon={FileText}>
              Terms
            </FooterLink>
            <p className="mt-2 inline-flex items-center gap-2">
              <Phone size={16} className="shrink-0 opacity-70" aria-hidden />
              <span>For emergencies call 112.</span>
            </p>
          </div>
        </div>
      </footer>
      <CiviChat />
    </div>
  );
}

export function Protected({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (loading) return;
    if (!user) navigate("/login", { replace: true, state: { from: location.pathname } });
    else if (roles && !roles.includes(user.role)) navigate(roleHome(user.role), { replace: true });
  }, [user, loading, roles, navigate, location.pathname]);

  const needsProfile =
    user?.role === "CITIZEN" &&
    !location.pathname.startsWith("/app/profile") &&
    location.pathname !== "/" &&
    !(user.locality || "").trim();

  const needsPhone =
    !!user &&
    !location.pathname.startsWith("/app/profile") &&
    location.pathname !== "/" &&
    !(user.phone || "").trim();

  useEffect(() => {
    if (loading || !user || !needsProfile) return;
    navigate("/app/profile", { replace: true, state: { from: location.pathname, setup: true } });
  }, [loading, user, needsProfile, navigate, location.pathname]);

  useEffect(() => {
    if (loading || !user || !needsPhone) return;
    navigate("/app/profile", { replace: true, state: { from: location.pathname, setup: true, needPhone: true } });
  }, [loading, user, needsPhone, navigate, location.pathname]);

  if (loading || !user) return <div className="card h-40 animate-pulse" />;
  if (roles && !roles.includes(user.role)) return null;
  if (needsProfile || needsPhone) return <div className="card h-40 animate-pulse" />;
  return <Outlet />;
}
