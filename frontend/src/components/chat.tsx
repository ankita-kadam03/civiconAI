import { MessageCircle, Send, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { endpoints } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Button, Card } from "./ui";

type ChatReport = {
  id: string;
  reference: string;
  title: string;
  summary: string;
  status: string;
  locality: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  publicReports?: ChatReport[];
  myReports?: ChatReport[];
  weather?: { available: boolean; summary?: string; temperature_c?: number | null; message?: string } | null;
};

export function CiviChat() {
  const { user } = useAuth();
  const userId = user?.id;
  const isSignedIn = Boolean(userId);
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Hi! I’m CiviChat. I can guide you around Civicon, find recent public issues and local weather, and help signed-in users find their own CIV references.",
    },
  ]);

  useEffect(() => {
    setHistory([
      {
        role: "assistant",
        content: isSignedIn
          ? "Hi! I’m CiviChat. I can guide you around Civicon, find recent public issues and local weather, and look up your CIV references."
          : "Hi! I’m CiviChat. I can guide you around Civicon, find recent public issues and local weather. Sign in when you want me to look up your own CIV references.",
      },
    ]);
  }, [isSignedIn, userId]);

  useEffect(() => {
    if (!open || coords || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => undefined,
      { maximumAge: 300000, timeout: 8000 },
    );
  }, [open, coords]);

  async function send() {
    const text = message.trim();
    if (!text || busy) return;
    setMessage("");
    const next = [...history, { role: "user" as const, content: text }];
    setHistory(next);
    setBusy(true);
    try {
      const res = await endpoints.chat({
        message: text,
        history: next.slice(-6).map(({ role, content }) => ({ role, content })),
        latitude: coords?.lat,
        longitude: coords?.lng,
      });
      setHistory([
        ...next,
        {
          role: "assistant",
          content: res.reply,
          publicReports: res.public_reports,
          myReports: res.my_reports,
          weather: res.weather,
        },
      ]);
    } catch {
      setHistory([
        ...next,
        { role: "assistant", content: "I couldn't reach the server. Try again or use Report an issue from the menu." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-3 z-40 sm:bottom-5 sm:right-5">
      {open ? (
        <Card className="mb-3 w-[min(92vw,380px)] border-teal/20 shadow-card dark:border-teal/30">
          <div className="mb-3 flex items-center gap-2 font-bold text-navy dark:text-white">
            <Sparkles size={16} className="text-teal" aria-hidden />
            CiviChat
          </div>
          <div className="mb-3 max-h-64 space-y-2 overflow-y-auto text-sm">
            {history.map((item, index) => (
              <div
                key={index}
                className={item.role === "user" ? "flex justify-end" : "flex justify-start"}
              >
                <div className="max-w-[90%]">
                  <p
                    className={
                      item.role === "user"
                        ? "rounded-2xl rounded-br-md bg-sky px-3 py-2 text-navy dark:bg-slate-700 dark:text-slate-100"
                        : "rounded-2xl rounded-bl-md bg-mint/70 px-3 py-2 text-navy dark:bg-slate-800 dark:text-slate-100"
                    }
                  >
                    {item.content}
                  </p>
                  {item.weather ? (
                    <div className="mt-2 rounded-xl border border-navy/10 bg-white p-2 text-xs dark:border-white/10 dark:bg-slate-900">
                      <p className="font-semibold">Local weather</p>
                      <p>
                        {item.weather.available
                          ? `${item.weather.summary}${item.weather.temperature_c != null ? ` (${Math.round(item.weather.temperature_c)}°C)` : ""}`
                          : item.weather.message}
                      </p>
                    </div>
                  ) : null}
                  {item.publicReports?.length ? (
                    <div className="mt-2 space-y-2">
                      {item.publicReports.map((report) => (
                        <Link
                          key={report.id}
                          to={`/explore/${encodeURIComponent(report.reference)}`}
                          onClick={() => setOpen(false)}
                          className="block rounded-xl border border-navy/10 bg-white p-2 text-xs text-navy hover:border-teal dark:border-white/10 dark:bg-slate-900 dark:text-white"
                        >
                          <span className="font-semibold">{report.reference} · {report.title}</span>
                          <span className="mt-1 block">{report.summary}</span>
                          <span className="mt-1 block text-navy/60 dark:text-slate-400">
                            {report.status} · {report.locality}
                          </span>
                        </Link>
                      ))}
                    </div>
                  ) : null}
                  {item.myReports?.length ? (
                    <div className="mt-2 space-y-2">
                      {item.myReports.map((report) => (
                        <Link
                          key={report.id}
                          to={`/app/reports/${encodeURIComponent(report.id)}`}
                          onClick={() => setOpen(false)}
                          className="block rounded-xl border border-teal/20 bg-white p-2 text-xs text-navy hover:border-teal dark:border-teal/30 dark:bg-slate-900 dark:text-white"
                        >
                          <span className="font-semibold">{report.reference} · {report.title}</span>
                          <span className="mt-1 block">{report.status} · {report.locality}</span>
                        </Link>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void send()}
              disabled={busy}
              className="flex-1 rounded-full border border-navy/10 bg-white px-3 py-2 text-sm text-navy dark:border-white/15 dark:bg-slate-900 dark:text-white"
              placeholder="Navigate or ask for nearby reports…"
            />
            <Button type="button" onClick={() => void send()} disabled={busy} aria-label="Send">
              <Send size={16} />
            </Button>
          </div>
          <p className="mt-2 text-[11px] text-navy/50 dark:text-slate-400">Navigation, nearby public reports, weather, and your reports when signed in.</p>
        </Card>
      ) : null}
      <Button type="button" onClick={() => setOpen((v) => !v)} className="shadow-card" aria-expanded={open}>
        <MessageCircle size={16} aria-hidden />
        CiviChat
      </Button>
    </div>
  );
}

/** @deprecated use CiviChat */
export const CiviGpt = CiviChat;
/** @deprecated use CiviChat */
export const HelperChat = CiviChat;
