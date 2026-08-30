import type { Currency } from "@/types";
import { formatByCurrency } from "@/utils/assets";

interface BalanceBreakdownProps {
  totalReceived: number;
  totalSpent: number;
  balance: number;
  currency: Currency;
}

export function BalanceBreakdown({ totalReceived, totalSpent, balance, currency }: BalanceBreakdownProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div className="rounded-lg border border-green-100 bg-green-50 p-3">
        <p className="text-xs font-medium text-green-700">Total Received</p>
        <p className="text-lg font-bold text-green-800">{formatByCurrency(totalReceived, currency)}</p>
      </div>
      <div className="rounded-lg border border-red-100 bg-red-50 p-3">
        <p className="text-xs font-medium text-red-700">Total Spent</p>
        <p className="text-lg font-bold text-red-800">{formatByCurrency(totalSpent, currency)}</p>
      </div>
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
        <p className="text-xs font-medium text-zinc-600">Current Balance</p>
        <p className="text-lg font-bold text-zinc-900">{formatByCurrency(balance, currency)}</p>
      </div>
    </div>
  );
}
