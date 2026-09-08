import { useMemo, useState } from "react";
import type { TransferRecipient } from "@/types";
import { Avatar } from "@/components/common/Avatar";
import { EmptyState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";

interface RecipientListProps {
  recipients: TransferRecipient[];
  isLoading: boolean;
  onSelect: (recipient: TransferRecipient) => void;
}

export function RecipientList({ recipients, isLoading, onSelect }: RecipientListProps) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return recipients;
    const q = search.trim().toLowerCase();
    return recipients.filter((r) => r.full_name.toLowerCase().includes(q) || r.username.toLowerCase().includes(q));
  }, [recipients, search]);

  return (
    <div>
      <div className="relative mb-4">
        <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or username..."
          className="input pl-9"
          aria-label="Search recipients"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title={recipients.length === 0 ? "No one to transfer to yet" : "No matches"}
          description={recipients.length === 0 ? "There are no other eligible users in your region." : "Try a different name or username."}
        />
      ) : (
        <div className="divide-y divide-zinc-100 rounded-xl border border-zinc-200">
          {filtered.map((r) => (
            <button
              key={r.id}
              onClick={() => onSelect(r)}
              className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-zinc-50"
            >
              <Avatar src={r.avatar_url} name={r.full_name} size="md" />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-zinc-900">{r.full_name}</p>
                <p className="truncate text-xs text-zinc-500">@{r.username}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
