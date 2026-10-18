import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, clearTokens, endpoints, setTokens } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (body: Record<string, unknown>) => Promise<User>;
  logout: () => void;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshMe() {
    try {
      const me = await endpoints.me();
      setUser(me);
    } catch {
      clearTokens();
      setUser(null);
    }
  }

  useEffect(() => {
    const token = localStorage.getItem("civicon.access");
    if (!token) {
      setLoading(false);
      return;
    }
    refreshMe().finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      async login(email, password) {
        const res = await endpoints.login({ email, password });
        setTokens(res.access_token, res.refresh_token);
        setUser(res.user);
        return res.user;
      },
      async signup(body) {
        const res = await endpoints.signup(body);
        setTokens(res.access_token, res.refresh_token);
        setUser(res.user);
        return res.user;
      },
      logout() {
        clearTokens();
        setUser(null);
        void api.post("/api/auth/logout").catch(() => undefined);
      },
      refreshMe,
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
