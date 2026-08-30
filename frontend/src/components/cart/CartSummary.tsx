import type { ReactNode } from "react";
import { formatBeans } from "@/utils/assets";

interface CartSummaryProps {
  total: number;
  balance: number;
  children?: ReactNode;
}

export function CartSummary({ total, balance, children }: CartSummaryProps) {
  const insufficient = balance < total;

  return (
    <div className="card sticky top-20 space-y-4 p-5">
      <h2 className="font-semibold text-zinc-900">Order Summary</h2>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between text-zinc-600">
          <span>Subtotal</span>
          <span className="font-medium text-zinc-900">{formatBeans(total)}</span>
        </div>
        <div className="flex justify-between text-zinc-600">
          <span>Your balance</span>
          <span className="font-medium text-zinc-900">{formatBeans(balance)}</span>
        </div>
        <div className="border-t border-zinc-100 pt-2">
          <div className="flex justify-between">
            <span className="font-semibold text-zinc-900">Total</span>
            <span className="text-lg font-bold text-zinc-900">{formatBeans(total)}</span>
          </div>
        </div>
      </div>
      {insufficient && total > 0 && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700">
          <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0 3.75h.008M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Insufficient balance. Ask an admin to add funds to your account.</span>
        </div>
      )}
      {children}
    </div>
  );
}
