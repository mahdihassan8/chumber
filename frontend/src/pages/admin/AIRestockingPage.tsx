import { useEffect, useState } from "react";
import { getRestockHistory } from "@/api/ai";
import type { AIRestockRequest } from "@/types";
import { AIChatPanel } from "@/components/ai/AIChatPanel";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { ApiRequestError } from "@/api/client";

export function AIRestockingPage() {
  const [requests, setRequests] = useState<AIRestockRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setIsLoading(true);
    setError(null);
    getRestockHistory()
      .then(setRequests)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load AI restock history"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const handleNewRequest = (request: AIRestockRequest) => setRequests((prev) => [request, ...prev]);
  const handleUpdated = (updated: AIRestockRequest) => setRequests((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));

  return (
    <div>
      <div className="mb-5">
        <h2 className="font-semibold text-zinc-900">AI Restocking Assistant</h2>
        <p className="text-sm text-zinc-500">Describe a restock in plain language or speak it — you'll always confirm before anything changes.</p>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <AIChatPanel requests={requests} onNewRequest={handleNewRequest} onUpdated={handleUpdated} />
      )}
    </div>
  );
}
