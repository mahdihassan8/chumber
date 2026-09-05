import { useEffect, useState } from "react";
import { getGiveaway } from "@/api/giveaway";
import type { GiveawayResult } from "@/types";
import { PageContainer } from "@/components/layout/PageContainer";
import { ProductImage } from "@/components/product/ProductImage";
import { Avatar } from "@/components/common/Avatar";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState, EmptyState } from "@/components/common/ErrorState";
import { formatDate } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

export function GiveawayPage() {
  const [result, setResult] = useState<GiveawayResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setIsLoading(true);
    setError(null);
    getGiveaway()
      .then(setResult)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load the giveaway"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  return (
    <PageContainer className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold text-zinc-900">Weekly Giveaway</h1>

      {isLoading ? (
        <Skeleton className="h-72 w-full" />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !result?.available ? (
        <EmptyState
          title="No giveaway yet"
          description="Winners are drawn every Sunday and Wednesday and revealed at 11:00 AM Baghdad time. Check back then."
        />
      ) : (
        <div className="space-y-6">
          <div
            className={`card flex items-center gap-3 p-5 ${
              result.is_winner ? "border-brand-300 bg-brand-50" : "bg-zinc-50"
            }`}
          >
            <p className="text-lg font-bold text-zinc-900">
              {result.is_winner ? "Congratulations 🎉" : "Good luck next time 🍀"}
            </p>
          </div>

          <div className="card flex flex-col items-center gap-4 p-6 text-center sm:flex-row sm:text-left">
            <ProductImage
              src={result.product_image_url}
              alt={result.product_name ?? "Prize"}
              className="h-28 w-28 shrink-0 rounded-xl"
            />
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">This week's prize</p>
              <p className="text-xl font-bold text-zinc-900">{result.product_name}</p>
              {result.scheduled_date && <p className="mt-1 text-sm text-zinc-500">Drawn {formatDate(result.scheduled_date)}</p>}
            </div>
          </div>

          <div className="card p-6">
            <p className="mb-4 text-sm font-semibold text-zinc-900">Winners</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {result.winners.map((winner) => (
                <div key={winner.id} className="flex items-center gap-3 rounded-lg border border-zinc-100 bg-zinc-50 p-3">
                  <Avatar src={null} name={winner.full_name} size="sm" />
                  <div className="min-w-0">
                    <p className="truncate font-medium text-zinc-900">{winner.full_name}</p>
                    <p className="truncate text-xs text-zinc-500">@{winner.username}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
}
