import { useEffect, useState } from "react";
import { getMyOrders } from "@/api/orders";
import type { Order } from "@/types";
import { PageContainer } from "@/components/layout/PageContainer";
import { OrderList } from "@/components/orders/OrderList";
import { ErrorState } from "@/components/common/ErrorState";
import { ApiRequestError } from "@/api/client";

export function PurchaseHistoryPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setIsLoading(true);
    setError(null);
    getMyOrders()
      .then(setOrders)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load purchase history"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  return (
    <PageContainer className="max-w-4xl">
      <h1 className="mb-6 text-2xl font-bold text-zinc-900">Purchase History</h1>
      {error ? <ErrorState message={error} onRetry={load} /> : <OrderList orders={orders} isLoading={isLoading} currency="beans" />}
    </PageContainer>
  );
}
