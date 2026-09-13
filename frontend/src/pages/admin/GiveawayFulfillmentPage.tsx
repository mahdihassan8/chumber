import { useEffect, useState } from "react";
import { getAdminGiveaways, setGiveawayWinnerFulfillment } from "@/api/giveaway";
import type { AdminGiveaway } from "@/types";
import { ProductImage } from "@/components/product/ProductImage";
import { Avatar } from "@/components/common/Avatar";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState, EmptyState } from "@/components/common/ErrorState";
import { useToast } from "@/context/ToastContext";
import { formatDate, formatDateTime } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

export function GiveawayFulfillmentPage() {
  const [giveaways, setGiveaways] = useState<AdminGiveaway[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const { showToast } = useToast();

  const load = () => {
    setIsLoading(true);
    setError(null);
    getAdminGiveaways()
      .then(setGiveaways)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load giveaways"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const toggleFulfilled = async (giveaway: AdminGiveaway, userId: string, fulfilled: boolean) => {
    const key = `${giveaway.id}:${userId}`;
    setBusyKey(key);
    try {
      const updated = await setGiveawayWinnerFulfillment(giveaway.id, userId, fulfilled);
      setGiveaways((prev) =>
        prev.map((g) =>
          g.id !== giveaway.id
            ? g
            : { ...g, winners: g.winners.map((w) => (w.user_id === userId ? updated : w)) }
        )
      );
      showToast(fulfilled ? "Marked as delivered" : "Marked as not yet delivered", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not update prize status", "error");
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div>
      <p className="mb-5 text-sm text-zinc-500">
        Track whether each Najaf giveaway winner has actually been handed their prize.
      </p>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : giveaways.length === 0 ? (
        <EmptyState title="No giveaways yet" description="Winners are drawn every Sunday and Wednesday." />
      ) : (
        <div className="space-y-4">
          {giveaways.map((giveaway) => {
            const pending = giveaway.winners.filter((w) => !w.fulfilled_at).length;
            return (
              <div key={giveaway.id} className="card p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <ProductImage
                      src={giveaway.product_image_url}
                      alt={giveaway.product_name}
                      className="h-14 w-14 shrink-0 rounded-lg"
                    />
                    <div>
                      <p className="font-semibold text-zinc-900">{giveaway.product_name}</p>
                      <p className="text-xs text-zinc-500">Drawn {formatDate(giveaway.scheduled_date)}</p>
                    </div>
                  </div>
                  <Badge color={pending === 0 ? "green" : "amber"}>
                    {pending === 0 ? "All delivered" : `${pending} pending`}
                  </Badge>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {giveaway.winners.map((winner) => {
                    const key = `${giveaway.id}:${winner.user_id}`;
                    return (
                      <div
                        key={winner.user_id}
                        className="flex items-center justify-between gap-3 rounded-lg border border-zinc-100 bg-zinc-50 p-3"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <Avatar src={null} name={winner.full_name} size="sm" />
                          <div className="min-w-0">
                            <p className="truncate font-medium text-zinc-900">{winner.full_name}</p>
                            <p className="truncate text-xs text-zinc-500">@{winner.username}</p>
                            {winner.fulfilled_at && (
                              <p className="truncate text-xs text-green-700">
                                Delivered {formatDateTime(winner.fulfilled_at)}
                                {winner.fulfilled_by_username && ` · by @${winner.fulfilled_by_username}`}
                              </p>
                            )}
                          </div>
                        </div>
                        <Button
                          variant={winner.fulfilled_at ? "ghost" : "primary"}
                          className="shrink-0 px-2.5 py-1.5 text-xs"
                          isLoading={busyKey === key}
                          onClick={() => toggleFulfilled(giveaway, winner.user_id, !winner.fulfilled_at)}
                        >
                          {winner.fulfilled_at ? "Undo" : "Mark delivered"}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
