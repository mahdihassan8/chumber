import { useEffect, useState } from "react";
import { getAllOrders } from "@/api/orders";
import type { Order } from "@/types";
import { OrderList } from "@/components/orders/OrderList";
import { ErrorState } from "@/components/common/ErrorState";
import { ApiRequestError } from "@/api/client";

export function OrderManagementPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setIsLoading(true);
    setError(null);
    getAllOrders()
      .then(setOrders)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load orders"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  return (
    <div>
      <p className="mb-5 text-sm text-zinc-500">{orders.length} order{orders.length === 1 ? "" : "s"} across all users</p>
      {error ? <ErrorState message={error} onRetry={load} /> : <OrderList orders={orders} isLoading={isLoading} showBuyer />}
    </div>
  );
}
