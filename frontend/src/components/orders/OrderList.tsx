import type { Order } from "@/types";
import { OrderCard } from "@/components/orders/OrderCard";
import { EmptyState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";

interface OrderListProps {
  orders: Order[];
  isLoading?: boolean;
  showBuyer?: boolean;
  currency?: "usd" | "beans";
}

export function OrderList({ orders, isLoading = false, showBuyer = false, currency = "usd" }: OrderListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (orders.length === 0) {
    return <EmptyState title="No orders yet" description="Purchases will show up here once you check out." />;
  }

  return (
    <div className="space-y-3">
      {orders.map((order) => (
        <OrderCard key={order.id} order={order} showBuyer={showBuyer} currency={currency} />
      ))}
    </div>
  );
}
