import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getMyBalance } from "@/api/balance";
import { useAuth } from "@/context/AuthContext";
import { useRegion } from "@/context/RegionContext";

interface BalanceContextValue {
  /** The signed-in account's balance for the current region, in IQD. null
   * while loading, on error, or while viewing "all regions" (there is no
   * single wallet to show then). */
  balance: number | null;
  isLoading: boolean;
  /** Re-fetches from the server and pushes the new value out to every
   * consumer (Navbar, Profile, Transfer Money, ...) immediately -- this is
   * what makes a balance-changing action show up everywhere without a page
   * refresh. */
  refresh: () => Promise<void>;
}

const BalanceContext = createContext<BalanceContextValue | undefined>(undefined);

/** Single source of truth for "my balance right now", shared app-wide so a
 * balance-changing action (like sending a transfer) only has to call
 * `refresh()` once and every display of it -- the navbar pill included --
 * updates together. Mirrors CartContext's shape/reasoning for the same kind
 * of cross-component staleness problem. */
export function BalanceProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { current } = useRegion();
  const [balance, setBalance] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) {
      setBalance(null);
      return;
    }
    setIsLoading(true);
    try {
      const b = await getMyBalance();
      setBalance(b.balance);
    } catch {
      // e.g. a Super Admin viewing "all regions" has no single wallet.
      setBalance(null);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
    // Also re-fetch on a region switch -- refresh() itself only depends on
    // `user`, but the wallet it reads is whichever region is currently
    // selected (sent as X-Region, not a parameter here).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, current]);

  return <BalanceContext.Provider value={{ balance, isLoading, refresh }}>{children}</BalanceContext.Provider>;
}

export function useBalance(): BalanceContextValue {
  const ctx = useContext(BalanceContext);
  if (!ctx) throw new Error("useBalance must be used within BalanceProvider");
  return ctx;
}
