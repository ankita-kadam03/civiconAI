export type Role = "CITIZEN" | "OFFICER" | "ADMIN" | "ADMIN_L1" | "ADMIN_L2" | "ADMIN_L3";
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Status =
  | "SUBMITTED"
  | "ACKNOWLEDGED"
  | "IN_PROGRESS"
  | "MORE_INFO_REQUESTED"
  | "ESCALATED"
  | "RESOLVED"
  | "CLOSED"
  | "REJECTED"
  | "reported"
  | "triaged"
  | "assigned"
  | "in_progress"
  | "resolved_pending_verification"
  | "closed"
  | "closed_unverified"
  | "reopened";

export interface User {
  id: string;
  email: string;
  display_name: string;
  phone?: string | null;
  role: Role;
  department_id?: string | null;
  locality?: string | null;
  date_of_birth?: string | null;
  is_active: boolean;
  demo_account?: boolean;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  icon?: string;
  description?: string;
  department_id?: string;
  review_hours?: number;
  resolve_hours?: number;
  is_active?: boolean;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  description?: string;
  contact_hint?: string;
}

export interface Complaint {
  id: string;
  reference: string;
  title: string;
  description?: string;
  summary?: string;
  category_id: string;
  department_id?: string | null;
  status: Status;
  severity: Severity;
  locality: string;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  occurred_at?: string | null;
  is_public: boolean;
  created_at?: string;
  updated_at?: string;
  resolved_at?: string | null;
  last_progress_at?: string | null;
  reporter_id?: string;
  assigned_officer_id?: string | null;
  category?: { id?: string; name?: string; slug?: string; icon?: string };
  department?: { id?: string; name?: string; code?: string } | null;
  reporter?: { id?: string; display_name?: string } | null;
  assignee?: { id?: string; display_name?: string } | null;
  similar?: Array<{ id: string; reference?: string; title?: string; score: number }>;
  ai?: Record<string, unknown>;
  ai_rationale?: string;
  ai_severity?: string;
  ai_category_slug?: string;
  history?: Array<{ id: string; from_status?: string; to_status?: string; note?: string; created_at?: string }>;
  comments?: Array<{ id: string; body: string; is_internal?: boolean; author_id?: string; created_at?: string }>;
  attachments?: Array<{ id: string; kind?: string; original_name?: string; mime_type?: string; is_private?: boolean }>;
  escalations?: Array<{ id: string; level?: number; reason?: string; created_at?: string }>;
  source?: string;
  escalation_level?: number;
  escalated_by_threshold?: boolean;
  human_review_required?: boolean;
  priority?: { score?: number; label?: string; factors?: Array<{ name: string; value: number; detail?: string }> };
  counters?: Record<string, number>;
  claimed_by?: string | null;
  sla?: { ack_due?: string | null; resolve_due?: string | null };
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  unread?: number;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  incident_id?: string;
  read_at?: string | null;
  created_at?: string;
}

export interface Analytics {
  total: number;
  active: number;
  resolved: number;
  overdue: number;
  resolution_rate: number;
  avg_resolution_hours: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_department: Record<string, number>;
  geo: Array<{ lat: number; lng: number; status?: string; severity?: string }>;
  hotspots?: Array<{ locality: string; count: number }>;
  department_performance?: Array<{ department: string; open: number; total: number }>;
  in_memory_data?: boolean;
  demo?: boolean;
  ai_platform?: string;
  bigquery?: {
    enabled?: boolean;
    recurrence_60d?: Array<{ locality: string; category: string; count: number }>;
    summary?: { total?: number; open?: number; last_7_days?: number };
  };
}

export interface ApiError {
  error?: { code?: string; message?: string; request_id?: string };
}
