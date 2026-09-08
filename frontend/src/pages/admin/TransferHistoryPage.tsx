import { useEffect, useState } from "react";
import { getAllTransfers } from "@/api/admin";
import type { Transfer } from "@/types";
import { TransferHistoryList } from "@/components/transfer/TransferHistoryList";
import { ErrorState } from "@/components/common/ErrorState";
import { ApiRequestError } from "@/api/client";

export function TransferHistoryPage() {
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setIsLoading(true);
    setError(null);
    getAllTransfers()
      .then(setTransfers)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load transfer history"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  return (
    <div>
      <p className="mb-5 text-sm text-zinc-500">
        {transfers.length} transfer{transfers.length === 1 ? "" : "s"} between users
      </p>
      {error ? <ErrorState message={error} onRetry={load} /> : <TransferHistoryList transfers={transfers} isLoading={isLoading} />}
    </div>
  );
}
