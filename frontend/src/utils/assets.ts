import { API_URL } from "@/api/client";

/** Predefined avatars live in the frontend's own /public dir; uploaded
 * avatars/product images are served by the backend under /uploads. */
export function resolveAssetUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("/uploads/")) return `${API_URL}${path}`;
  return path;
}

export function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

/** Admin-side money display. Iraqi Dinar has no subunit in circulation and no
 * symbol worth using, so it renders as a whole number with thousands
 * separators and a trailing "IQD" label. */
export function formatIQD(amount: number): string {
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(amount)} IQD`;
}

/** The backend stores everything in IQD — this is a display-only conversion
 * for the marketplace/shopper-facing UI, which shows "Beans" instead: whole
 * numbers, no symbol, no decimals. 250 IQD = 1 Bean (so 1,000 IQD = 4 Beans).
 * Beans never appear in the Admin Dashboard, and IQD never appears in the
 * shopper-facing UI. */
export const IQD_PER_BEAN = 250;

export function toBeans(iqdAmount: number): number {
  return Math.round(iqdAmount / IQD_PER_BEAN);
}

export function formatBeans(iqdAmount: number): string {
  return new Intl.NumberFormat("en-US").format(toBeans(iqdAmount));
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
