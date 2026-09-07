import type { Region, User, UserRole } from "@/types";

/** Roles with Admin Dashboard access. The hierarchy is
 * customer < admin < super_admin, so a Super Admin can do everything an Admin
 * can — mirrors core/deps.require_admin on the backend. */
export const ADMIN_ROLES: UserRole[] = ["admin", "super_admin"];

export function isAdmin(user: Pick<User, "role"> | null | undefined): boolean {
  return !!user && ADMIN_ROLES.includes(user.role);
}

export function isSuperAdmin(user: Pick<User, "role"> | null | undefined): boolean {
  return user?.role === "super_admin";
}

/** Human-readable role label ("super admin" rather than "super_admin"). */
export function roleLabel(role: UserRole): string {
  return role === "super_admin" ? "super admin" : role;
}

export function roleBadgeColor(role: UserRole): "amber" | "blue" | "zinc" {
  if (role === "super_admin") return "amber";
  return role === "admin" ? "blue" : "zinc";
}

export const REGIONS: Region[] = ["baghdad", "najaf"];

/** "baghdad" -> "Baghdad". Unassigned accounts/products render as a dash. */
export function regionLabel(region: Region | null | undefined): string {
  if (!region) return "—";
  return region.charAt(0).toUpperCase() + region.slice(1);
}

export function regionBadgeColor(region: Region | null | undefined): "green" | "blue" | "zinc" {
  if (region === "baghdad") return "green";
  if (region === "najaf") return "blue";
  return "zinc";
}
