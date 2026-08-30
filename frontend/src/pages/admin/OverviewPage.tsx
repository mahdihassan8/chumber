import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getOverview } from "@/api/admin";
import type { OverviewStats } from "@/types";
import { StatCard } from "@/components/admin/StatCard";
import { OrderList } from "@/components/orders/OrderList";
import { TransactionList } from "@/components/balance/TransactionList";
import { ErrorState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";
import { formatCurrency } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

const ICONS = {
  users: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z",
  box: "M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z",
  warning: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
  orders: "M8.25 3v1.5M15.75 3v1.5M3 6.75h18M3.75 6.75h16.5v13.5a1.5 1.5 0 01-1.5 1.5H5.25a1.5 1.5 0 01-1.5-1.5V6.75z",
  cash: "M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z",
};

function Icon({ path }: { path: string }) {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}

export function OverviewPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    getOverview()
      .then(setStats)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load dashboard"));
  };

  useEffect(load, []);

  if (error) return <ErrorState message={error} onRetry={load} />;

  if (!stats) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Users" value={stats.total_users} icon={<Icon path={ICONS.users} />} />
        <StatCard label="Customers" value={stats.total_customers} icon={<Icon path={ICONS.users} />} />
        <StatCard label="Admins" value={stats.total_admins} icon={<Icon path={ICONS.users} />} />
        <StatCard label="Total Products" value={stats.total_products} icon={<Icon path={ICONS.box} />} />
        <StatCard label="Available Products" value={stats.available_products} icon={<Icon path={ICONS.box} />} />
        <StatCard label="Out of Stock" value={stats.out_of_stock_products} icon={<Icon path={ICONS.warning} />} tone="warning" />
        <StatCard label="Total Orders" value={stats.total_orders} icon={<Icon path={ICONS.orders} />} />
        <StatCard label="Balance Distributed" value={formatCurrency(stats.total_balance_distributed)} icon={<Icon path={ICONS.cash} />} />
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold text-zinc-900">Recent Orders</h2>
            <Link to="/admin/orders" className="text-sm font-medium text-brand-600 hover:text-brand-700">
              View all
            </Link>
          </div>
          <OrderList orders={stats.recent_orders} />
        </section>
        <section>
          <h2 className="mb-3 font-semibold text-zinc-900">Recent Balance Activity</h2>
          <div className="card p-4">
            <TransactionList transactions={stats.recent_transactions} />
          </div>
        </section>
      </div>
    </div>
  );
}
