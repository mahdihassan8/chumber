import { useBalance } from "@/context/BalanceContext";

/** The signed-in account's balance **for the current region**.
 *
 * Thin proxy over the shared BalanceContext (one fetch, one source of truth
 * for every consumer) so this hook's existing call sites -- the navbar pill,
 * the Profile page -- don't need to change, but all still update together
 * the instant something elsewhere (e.g. a Transfer Money send) calls
 * useBalance().refresh(), with no page reload required.
 */
export function useOwnBalance(): number | null {
  return useBalance().balance;
}
