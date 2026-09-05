import { useEffect, useState } from "react";
import { listUsers } from "@/api/users";
import type { User } from "@/types";
import { UserBalanceRow } from "@/components/balance/UserBalanceRow";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState, EmptyState } from "@/components/common/ErrorState";
import { formatIQD } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

export function BalanceManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const load = () => {
    setIsLoading(true);
    setError(null);
    listUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load users"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const handleBalanceChanged = (userId: string, newBalance: number) => {
    setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, balance: newBalance } : u)));
  };

  const totalDistributed = users.reduce((sum, u) => sum + u.balance, 0);
  const filtered = users.filter((u) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return u.username.toLowerCase().includes(q) || u.full_name.toLowerCase().includes(q);
  });

  return (
    <div>
      <div className="card mb-5 flex items-center gap-4 p-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z" />
          </svg>
        </div>
        <div>
          <p className="text-sm text-zinc-500">Total balance across all users</p>
          <p className="text-xl font-bold text-zinc-900">{formatIQD(totalDistributed)}</p>
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search users..." className="input max-w-xs" />
        <p className="text-sm text-zinc-500">Click a user to see their full breakdown and transaction history</p>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState title="No users found" />
      ) : (
        <div className="space-y-3">
          {filtered.map((u) => (
            <UserBalanceRow key={u.id} user={u} onBalanceChanged={handleBalanceChanged} />
          ))}
        </div>
      )}
    </div>
  );
}
