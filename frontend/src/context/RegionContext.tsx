import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Region } from "@/types";
import { getRegion, setRegion as persistRegion } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { isSuperAdmin } from "@/utils/roles";

interface RegionContextValue {
  /** The region the app is currently showing. null means "all regions", which
   * only a Super Admin can select. */
  current: Region | "all" | null;
  /** Regions this account may use — drives whether a switcher is shown at all. */
  allowed: Region[];
  switchRegion: (region: Region | "all") => void;
}

const RegionContext = createContext<RegionContextValue | undefined>(undefined);

export function RegionProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [current, setCurrent] = useState<Region | "all" | null>(() => (getRegion() as Region | "all" | null) ?? null);

  const allowed = useMemo<Region[]>(() => {
    if (!user) return [];
    // A Super Admin is global, so it can act in either region even though its
    // own membership rows are incidental.
    return isSuperAdmin(user) ? (["najaf", "baghdad"] as Region[]) : user.regions;
  }, [user]);

  // Keep the stored region legal: if the account lost access to it (or never
  // had it), fall back to the first region it does hold. The backend would
  // reject the stale value anyway — this just avoids a screen full of errors.
  useEffect(() => {
    if (!user) return;
    const isAll = current === "all";
    const legal = isAll ? isSuperAdmin(user) : current !== null && allowed.includes(current);
    if (!legal) {
      const next = isSuperAdmin(user) ? "all" : (allowed[0] ?? null);
      setCurrent(next);
      persistRegion(next);
    }
  }, [user, allowed, current]);

  const switchRegion = useCallback((region: Region | "all") => {
    setCurrent(region);
    persistRegion(region);
    // Regional data is cached all over the page tree; a hard reload is the
    // simplest way to guarantee nothing from the previous region survives on
    // screen, which is exactly what the isolation rules require.
    window.location.reload();
  }, []);

  return <RegionContext.Provider value={{ current, allowed, switchRegion }}>{children}</RegionContext.Provider>;
}

export function useRegion(): RegionContextValue {
  const ctx = useContext(RegionContext);
  if (!ctx) throw new Error("useRegion must be used within a RegionProvider");
  return ctx;
}
