import { useState } from "react";
import type { Currency } from "@/types";
import { setUserCurrency } from "@/api/balance";
import { useToast } from "@/context/ToastContext";
import { ApiRequestError } from "@/api/client";

interface CurrencySwitcherProps {
  userId: string;
  currency: Currency;
  /** Called after a successful switch with the confirmed currency/balance
   * from the server, so the caller can sync its own state. */
  onChanged: (currency: Currency, balance: number) => void;
  className?: string;
}

export function CurrencySwitcher({ userId, currency, onChanged, className = "" }: CurrencySwitcherProps) {
  const { showToast } = useToast();
  const [isSaving, setIsSaving] = useState(false);

  const handleChange = async (next: Currency) => {
    if (next === currency || isSaving) return;
    setIsSaving(true);
    try {
      const updated = await setUserCurrency(userId, next);
      onChanged(updated.currency, updated.balance);
      showToast(`Balance currency switched to ${updated.currency}`, "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not switch currency", "error");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <select
      aria-label="Balance currency"
      className={`input w-auto py-1.5 text-xs ${className}`}
      value={currency}
      disabled={isSaving}
      onChange={(e) => handleChange(e.target.value as Currency)}
    >
      <option value="USD">USD</option>
      <option value="IQD">IQD</option>
    </select>
  );
}
