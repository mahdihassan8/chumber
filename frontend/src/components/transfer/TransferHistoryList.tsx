import type { Transfer } from "@/types";
import { Avatar } from "@/components/common/Avatar";
import { Badge } from "@/components/common/Badge";
import { BeansAmount } from "@/components/common/BeansAmount";
import { EmptyState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";
import { formatDateTime, formatIQD } from "@/utils/assets";

const DELETED_LABEL = "Deleted user";

interface TransferHistoryListProps {
  transfers: Transfer[];
  isLoading?: boolean;
  /** The signed-in account's id -- when given, each row is framed from their
   * point of view ("Sent to" / "Received from", Beans, directional color).
   * Omitted for the Admin Dashboard view, which instead shows both parties
   * and a region badge, in IQD like the rest of the Admin Dashboard. */
  currentUserId?: string;
}

export function TransferHistoryList({ transfers, isLoading = false, currentUserId }: TransferHistoryListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (transfers.length === 0) {
    return <EmptyState title="No transfers yet" description="Money sent or received between users will show up here." />;
  }

  return (
    <div className="space-y-3">
      {transfers.map((t) => {
        if (currentUserId) {
          const isSent = t.sender_id === currentUserId;
          const otherName = (isSent ? t.recipient_full_name : t.sender_full_name) ?? DELETED_LABEL;
          const otherUsername = isSent ? t.recipient_username : t.sender_username;
          const otherAvatar = isSent ? t.recipient_avatar_url : t.sender_avatar_url;

          return (
            <div key={t.id} className="card flex items-center justify-between gap-4 p-4">
              <div className="flex min-w-0 items-center gap-3">
                <Avatar src={otherAvatar} name={otherName} size="md" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-zinc-900">
                    {isSent ? "Sent to " : "Received from "}
                    {otherName}
                  </p>
                  <p className="truncate text-xs text-zinc-500">
                    {otherUsername && <>@{otherUsername} · </>}
                    {formatDateTime(t.created_at)}
                  </p>
                  {t.note && <p className="mt-0.5 truncate text-xs text-zinc-400">"{t.note}"</p>}
                </div>
              </div>
              <span className={`shrink-0 font-bold tabular-nums ${isSent ? "text-zinc-900" : "text-green-600"}`}>
                {isSent ? "-" : "+"}
                <BeansAmount amount={t.amount} />
              </span>
            </div>
          );
        }

        return (
          <div key={t.id} className="card flex items-center justify-between gap-4 p-4">
            <div className="flex min-w-0 items-center gap-3">
              <Avatar src={t.sender_avatar_url} name={t.sender_full_name ?? DELETED_LABEL} size="sm" />
              <svg className="h-4 w-4 shrink-0 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
              <Avatar src={t.recipient_avatar_url} name={t.recipient_full_name ?? DELETED_LABEL} size="sm" />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-zinc-900">
                  {t.sender_full_name ?? DELETED_LABEL} → {t.recipient_full_name ?? DELETED_LABEL}
                </p>
                <p className="truncate text-xs text-zinc-500">
                  {formatDateTime(t.created_at)}
                  {t.note && <> · "{t.note}"</>}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge color="zinc">{t.region}</Badge>
              <span className="font-bold text-zinc-900">{formatIQD(t.amount)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
