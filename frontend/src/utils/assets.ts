import { API_URL } from "@/api/client";
import type { Currency } from "@/types";

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

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
}

/** Formats a balance figure in the owning account's currency (User.currency
 * / Balance.currency) — no conversion. IQD has no ISO currency formatting
 * convention worth relying on here, so it's rendered as a plain number with
 * a trailing "IQD" label rather than through Intl's currency style; USD
 * shows the `$` symbol via formatCurrency. */
export function formatByCurrency(amount: number, currency: Currency): string {
  if (currency === "IQD") {
    return `${new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount)} IQD`;
  }
  return formatCurrency(amount);
}

/** The backend stores and the Admin Dashboard operates in USD — this is a
 * display-only conversion for the marketplace/shopper-facing UI, which shows
 * "Beans" instead: whole numbers, no currency symbol, no decimals. */
export const USD_TO_BEANS_RATE = 4;

export function toBeans(usdAmount: number): number {
  return Math.round(usdAmount * USD_TO_BEANS_RATE);
}

export function formatBeans(usdAmount: number): string {
  return new Intl.NumberFormat("en-US").format(toBeans(usdAmount));
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
