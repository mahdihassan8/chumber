import { useRegion } from "@/context/RegionContext";
import { useAuth } from "@/context/AuthContext";
import { isSuperAdmin } from "@/utils/roles";
import { regionLabel } from "@/utils/roles";
import type { Region } from "@/types";

/** Only rendered when there is actually a choice to make: an account with a
 * single region has nothing to switch between. */
export function RegionSwitcher({ className = "" }: { className?: string }) {
  const { current, allowed, switchRegion } = useRegion();
  const { user } = useAuth();
  const canSeeAll = isSuperAdmin(user);

  if (allowed.length < 2 && !canSeeAll) return null;

  return (
    <select
      aria-label="Current region"
      value={current ?? ""}
      onChange={(e) => switchRegion(e.target.value as Region | "all")}
      className={`rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-sm font-medium text-zinc-700 focus:border-brand-500 focus:outline-none ${className}`}
    >
      {canSeeAll && <option value="all">All regions</option>}
      {allowed.map((r) => (
        <option key={r} value={r}>
          {regionLabel(r)}
        </option>
      ))}
    </select>
  );
}
