import type { Role } from "../../lib/types";

export function roleHome(role?: Role) {
  if (role === "ADMIN" || role === "ADMIN_L3") return "/admin";
  if (role === "ADMIN_L2") return "/l2";
  if (role === "OFFICER" || role === "ADMIN_L1") return "/officer";
  return "/app";
}

export const STAFF_ROLES: Role[] = ["OFFICER", "ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3"];
export const L1_ROLES: Role[] = ["OFFICER", "ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3"];
export const L2_ROLES: Role[] = ["ADMIN_L2", "ADMIN", "ADMIN_L3"];
export const L3_ROLES: Role[] = ["ADMIN", "ADMIN_L3"];

export function notificationTabs(role?: Role): string[] {
  if (role === "ADMIN_L3") return ["escalated", "persistent", "digest"];
  if (role === "ADMIN_L2") return ["escalated", "new_in_region", "overdue"];
  if (role === "OFFICER" || role === "ADMIN_L1" || role === "ADMIN") return ["inbox", "new_in_region", "overdue"];
  return ["for_you", "nearby", "alerts"];
}
