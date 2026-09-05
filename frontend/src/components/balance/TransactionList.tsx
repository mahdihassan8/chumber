import type { BalanceTransaction } from "@/types";
import { Badge } from "@/components/common/Badge";
import { EmptyState } from "@/components/common/ErrorState";
import { formatBeans, formatIQD, formatDateTime } from "@/utils/assets";

const TYPE_LABEL: Record<BalanceTransaction["transaction_type"], string> = {
  admin_recharge: "Admin Recharge",
  purchase: "Purchase",
  refund: "Refund",
  adjustment: "Adjustment",
};

const TYPE_COLOR: Record<BalanceTransaction["transaction_type"], "green" | "red" | "blue" | "amber"> = {
  admin_recharge: "green",
  purchase: "red",
  refund: "blue",
  adjustment: "amber",
};

interface TransactionListProps {
  transactions: BalanceTransaction[];
  /** Admin Dashboard views (default) show raw IQD. The shopper-facing
   * Profile page passes "beans" to show the converted marketplace unit
   * instead. */
  currency?: "iqd" | "beans";
}

export function TransactionList({ transactions, currency = "iqd" }: TransactionListProps) {
  const format = (txn: BalanceTransaction) => (currency === "beans" ? formatBeans(txn.amount) : formatIQD(txn.amount));

  if (transactions.length === 0) {
    return <EmptyState title="No transactions yet" description="Balance activity will show up here." />;
  }

  return (
    <div className="divide-y divide-zinc-100">
      {transactions.map((txn) => (
        <div key={txn.id} className="flex items-center justify-between gap-4 py-3">
          <div className="flex items-center gap-3">
            <Badge color={TYPE_COLOR[txn.transaction_type]}>{TYPE_LABEL[txn.transaction_type]}</Badge>
            <div>
              {txn.description && <p className="text-sm text-zinc-700">{txn.description}</p>}
              <p className="text-xs text-zinc-400">
                {formatDateTime(txn.created_at)}
                {txn.created_by_username && <> · by @{txn.created_by_username}</>}
              </p>
            </div>
          </div>
          <span className={`shrink-0 font-semibold tabular-nums ${txn.amount >= 0 ? "text-green-600" : "text-zinc-900"}`}>
            {txn.amount >= 0 ? "+" : ""}
            {format(txn)}
          </span>
        </div>
      ))}
    </div>
  );
}
