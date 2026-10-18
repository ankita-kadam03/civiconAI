import { config } from "./config";
import type { Analytics, ApiError, Category, Complaint, Department, NotificationItem, Page, User } from "./types";

const ACCESS = "civicon.access";
const REFRESH = "civicon.refresh";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS, access);
  localStorage.setItem(REFRESH, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
}

class ApiClientError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function parseError(res: Response): Promise<ApiClientError> {
  let message = "Request failed";
  let code: string | undefined;
  try {
    const body = (await res.json()) as ApiError;
    message = body.error?.message || message;
    code = body.error?.code;
  } catch {
    message = res.statusText || message;
  }
  return new ApiClientError(message, res.status, code);
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getAccessToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${config.apiBase}${path}`, { ...init, headers });
  if (res.status === 401 && retry && localStorage.getItem(REFRESH)) {
    const refreshed = await fetch(`${config.apiBase}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: localStorage.getItem(REFRESH) }),
    });
    if (refreshed.ok) {
      const body = (await refreshed.json()) as { access_token: string; refresh_token: string };
      setTokens(body.access_token, body.refresh_token);
      return request<T>(path, init, false);
    }
    clearTokens();
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  error: ApiClientError,
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, file: File, kind = "report") => {
    const data = new FormData();
    data.append("file", file);
    return request<T>(`${path}?kind=${encodeURIComponent(kind)}`, { method: "POST", body: data });
  },
};

export const endpoints = {
  health: () => api.get<{ ok: boolean; memory_database: boolean; database: string }>("/health"),
  bootstrap: () =>
    api.get<{
      service_area: {
        name: string;
        code: string;
        municipality_bounds?: {
          center?: { lat: number; lng: number };
          radius_m?: number;
          min_lat?: number;
          max_lat?: number;
          min_lng?: number;
          max_lng?: number;
        } | null;
        regions?: Array<{ code: string; name: string; level: number; radius_m?: number }>;
      };
      google_cloud: { project: string | null; location: string };
      map_center: { lat: number; lng: number } | null;
      municipality_bounds?: { center: { lat: number; lng: number }; radius_m: number } | null;
      regions?: Array<{ code: string; name: string; level: number; radius_m?: number }>;
      test_accounts: Array<{ email: string; role: string; authority_level?: number; region?: string | null }>;
      integrations: Record<string, unknown>;
      pubsub_note: string;
      push_note: string;
    }>("/api/public/bootstrap"),
  categories: () => api.get<Category[]>("/api/public/categories"),
  departments: () => api.get<Department[]>("/api/public/departments"),
  localities: () => api.get<Array<{ id: string; code: string; name: string }>>("/api/public/localities"),
  publicComplaints: (params = "") => api.get<Page<Complaint>>(`/api/public/complaints${params}`),
  publicComplaint: (reference: string) => api.get<Complaint>(`/api/public/complaints/${reference}`),
  signup: (body: unknown) => api.post<{ access_token: string; refresh_token: string; user: User }>("/api/auth/signup", body),
  login: (body: unknown) => api.post<{ access_token: string; refresh_token: string; user: User }>("/api/auth/login", body),
  me: () => api.get<User>("/api/auth/me"),
  forgot: (email: string) => api.post<{ ok: boolean; reset_token?: string; message: string }>("/api/auth/forgot-password", { email }),
  reset: (token: string, password: string) => api.post("/api/auth/reset-password", { token, password }),
  profile: (body: unknown) => api.patch<User>("/api/users/me", body),
  changePassword: (body: unknown) => api.post("/api/auth/change-password", body),
  complaints: (params = "") => api.get<Page<Complaint>>(`/api/complaints${params}`),
  complaint: (id: string) => api.get<Complaint>(`/api/complaints/${id}`),
  deleteComplaint: (id: string) => api.delete(`/api/complaints/${id}`),
  createComplaint: (body: unknown) => api.post<Complaint>("/api/complaints", body),
  status: (id: string, body: unknown) => api.patch<Complaint>(`/api/complaints/${id}/status`, body),
  comment: (id: string, body: unknown) => api.post(`/api/complaints/${id}/comments`, body),
  assign: (id: string, body: unknown) => api.post(`/api/complaints/${id}/assign`, body),
  escalate: (id: string, reason: string) => api.post(`/api/complaints/${id}/escalate`, { reason }),
  attach: (id: string, file: File, kind = "report") => api.upload(`/api/complaints/${id}/attachments`, file, kind),
  notifications: () => api.get<Page<NotificationItem>>("/api/notifications"),
  readNotification: (id: string) => api.post(`/api/notifications/${id}/read`),
  readAll: () => api.post("/api/notifications/read-all"),
  classify: (body: unknown) => api.post("/api/ai/classify", body),
  chat: (body: unknown) => api.post<{ reply: string; ai_generated: boolean; disclaimer: string }>("/api/ai/chat", body),
  analytics: () => api.get<Analytics>("/api/admin/analytics"),
  users: (q = "") => api.get<User[]>(`/api/admin/users${q}`),
  patchUser: (id: string, body: unknown) => api.patch<User>(`/api/admin/users/${id}`, body),
  officers: () => api.get<User[]>("/api/admin/officers"),
  adminCategories: () => api.get<Category[]>("/api/admin/categories"),
  createCategory: (body: unknown) => api.post("/api/admin/categories", body),
  patchCategory: (id: string, body: unknown) => api.patch(`/api/admin/categories/${id}`, body),
  adminDepartments: () => api.get<Department[]>("/api/admin/departments"),
  createDepartment: (body: unknown) => api.post("/api/admin/departments", body),
  patchDepartment: (id: string, body: unknown) => api.patch(`/api/admin/departments/${id}`, body),
  rules: () => api.get<Array<Record<string, unknown>>>("/api/admin/escalation-rules"),
  createRule: (body: unknown) => api.post("/api/admin/escalation-rules", body),
  patchRule: (id: string, body: unknown) => api.patch(`/api/admin/escalation-rules/${id}`, body),
  audit: () => api.get<Page<Record<string, unknown>>>("/api/admin/audit"),
  escalations: () => api.get<Array<Record<string, unknown>>>("/api/admin/escalations"),
  integrations: () => api.get<Record<string, Record<string, unknown>>>("/api/admin/integrations"),
  weather: (lat: number, lng: number) => api.get(`/api/public/weather?lat=${lat}&lng=${lng}`),
  promote: (id: string) => api.post(`/api/v1/incidents/${id}/promote`),
  better: (id: string) => api.post(`/api/v1/incidents/${id}/better`),
  verify: (id: string, answer: "resolved" | "unresolved") => api.post(`/api/v1/incidents/${id}/verify`, { answer }),
  claim: (id: string) => api.post(`/api/v1/admin/incidents/${id}/claim`),
  savedLocations: () => api.get<{ items: Array<Record<string, unknown>> }>("/api/v1/me/saved-locations"),
  saveLocation: (body: unknown) => api.post("/api/v1/me/saved-locations", body),
  deleteLocation: (id: string) => api.delete(`/api/v1/me/saved-locations/${id}`),
  savePrefs: (body: unknown) => api.put("/api/v1/me/notification-prefs", body),
  v1Notifications: (tab: string) => api.get<Page<NotificationItem>>(`/api/v1/notifications?tab=${encodeURIComponent(tab)}`),
};

export function attachmentUrl(id: string, isPublic = false): string {
  const token = getAccessToken();
  const path = isPublic ? `/api/public/attachments/${id}` : `/api/attachments/${id}`;
  if (isPublic) return `${config.apiBase}${path}`;
  return `${config.apiBase}${path}${token ? "" : ""}`;
}

export async function fetchAttachmentBlob(id: string): Promise<string> {
  const token = getAccessToken();
  const res = await fetch(`${config.apiBase}/api/attachments/${id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new Error("Could not load attachment");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
