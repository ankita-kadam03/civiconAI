import { MessageCircle, Send, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { endpoints } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Button, Card } from "./ui";

export function CiviChat() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [history, setHistory] = useState<Array<{ role: "user" | "assistant"; content: string }>>([
    {
      role: "assistant",
      content:
        "I'm CiviChat. I help with Civicon screen navigation and listing recent public reports near you. I can't answer other topics.",
    },
  ]);

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
    if (!user) {
      setHistory((h) => [
        ...h,
        { role: "user", content: text },
        { role: "assistant", content: "Sign in first — then I can fetch reports near you. You can still use Explore on the home page while signed out." },
      ]);
      setMessage("");
      return;
    }
    setMessage("");
    const next = [...history, { role: "user" as const, content: text }];
    setHistory(next);
    setBusy(true);
    try {
      const res = await endpoints.chat({
        message: text,
        history: next.slice(-6),
        latitude: coords?.lat,
        longitude: coords?.lng,
      });
      setHistory([...next, { role: "assistant", content: res.reply }]);
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
    <div className="fixed bottom-5 right-5 z-40">
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
                <p
                  className={
                    item.role === "user"
                      ? "max-w-[85%] rounded-2xl rounded-br-md bg-sky px-3 py-2 text-navy dark:bg-slate-700 dark:text-slate-100"
                      : "max-w-[85%] rounded-2xl rounded-bl-md bg-mint/70 px-3 py-2 text-navy dark:bg-slate-800 dark:text-slate-100"
                  }
                >
                  {item.content}
                </p>
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
          <p className="mt-2 text-[11px] text-navy/50 dark:text-slate-400">Navigation and nearby public reports only.</p>
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
