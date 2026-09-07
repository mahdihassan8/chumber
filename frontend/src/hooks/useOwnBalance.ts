import { useEffect, useState } from "react";
import { getMyBalance } from "@/api/balance";
import { useAuth } from "@/context/AuthContext";
import { useRegion } from "@/context/RegionContext";

/** The signed-in account's balance **for the current region**.
 *
 * Balances are per region now, so this can't come from the auth payload any
 * more — it is fetched from /api/balance, which the backend scopes to the
 * region this request nominated. Re-fetches whenever the region changes.
 */
export function useOwnBalance(): number | null {
  const { user } = useAuth();
  const { current } = useRegion();
  const [balance, setBalance] = useState<number | null>(null);

  useEffect(() => {
    if (!user) {
      setBalance(null);
      return;
    }
    let cancelled = false;
    getMyBalance()
      .then((b) => !cancelled && setBalance(b.balance))
      .catch(() => !cancelled && setBalance(null));
    return () => {
      cancelled = true;
    };
  }, [user, current]);

  return balance;
}
