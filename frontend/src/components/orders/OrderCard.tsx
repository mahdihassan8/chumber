import { useState } from "react";
import { Link } from "react-router-dom";
import type { Order } from "@/types";
import { Badge } from "@/components/common/Badge";
import { BeansAmount } from "@/components/common/BeansAmount";
import { formatIQD, formatDateTime } from "@/utils/assets";

interface OrderCardProps {
  order: Order;
  /** Show a clickable buyer name/username — for admin views listing orders across multiple users. */
  showBuyer?: boolean;
  /** Admin Dashboard views (default) show IQD, the stored unit. The
   * shopper-facing Purchase History page passes "beans" instead. */
  currency?: "iqd" | "beans";
}

export function OrderCard({ order, showBuyer = false, currency = "iqd" }: OrderCardProps) {
  const [expanded, setExpanded] = useState(false);
  const renderAmount = (amount: number) => (currency === "beans" ? <BeansAmount amount={amount} /> : formatIQD(amount));

  return (
    <div className="card overflow-hidden">
      <div className="flex w-full items-center justify-between gap-4 p-4">
        <button onClick={() => setExpanded((v) => !v)} className="flex flex-1 items-center gap-3 text-left">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-zinc-500">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M15.75 3v1.5M3 6.75h18M3.75 6.75h16.5v13.5a1.5 1.5 0 01-1.5 1.5H5.25a1.5 1.5 0 01-1.5-1.5V6.75z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-900">Order #{order.id.slice(0, 8).toUpperCase()}</p>
            <p className="text-xs text-zinc-500">{formatDateTime(order.created_at)}</p>
          </div>
        </button>
        {showBuyer && (
          <Link
            to={`/admin/users/${order.user_id}`}
            onClick={(e) => e.stopPropagation()}
            className="text-sm font-medium text-brand-600 hover:text-brand-700 hover:underline"
          >
            {order.user_full_name}
            <span className="text-zinc-400"> (@{order.user_username})</span>
          </Link>
        )}
        <button onClick={() => setExpanded((v) => !v)} className="flex items-center gap-3">
          <Badge color={order.status === "completed" ? "green" : "red"}>{order.status}</Badge>
          <span className="font-bold text-zinc-900">{renderAmount(order.total_amount)}</span>
          <svg className={`h-4 w-4 text-zinc-400 transition-transform ${expanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
      </div>
      {expanded && (
        <div className="divide-y divide-zinc-100 border-t border-zinc-100 px-4">
          {order.items.map((item) => (
            <div key={item.id} className="flex items-center justify-between py-2.5 text-sm">
              <span className="text-zinc-700">
                {item.product_name} <span className="text-zinc-400">× {item.quantity}</span>
              </span>
              <span className="font-medium text-zinc-900">{renderAmount(item.subtotal)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
