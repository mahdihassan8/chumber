import { useEffect, useState, type FormEvent } from "react";
import { clearTotalDebts, getTotalDebts, setTotalDebts } from "@/api/admin";
import { useToast } from "@/context/ToastContext";
import { ApiRequestError } from "@/api/client";
import { TextField } from "@/components/common/TextField";
import { Button } from "@/components/common/Button";
import { Spinner } from "@/components/common/Spinner";
import { formatIQD } from "@/utils/assets";

/** Admin Dashboard section for the current region's manually-entered "total
 * debts" figure: a single editable amount, persisted server-side. Feeds the
 * Balance Difference calculation on this page. Clearing only resets the
 * value back to empty — the section and its input stay right here. */
export function TotalDebtsCard() {
  const { showToast } = useToast();
  const [amount, setAmount] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [amountInput, setAmountInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const load = () => {
    setIsLoading(true);
    getTotalDebts()
      .then((r) => setAmount(r.amount))
      .catch((err) => showToast(err instanceof ApiRequestError ? err.message : "Could not load total debts", "error"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const startEditing = () => {
    setAmountInput(amount !== null ? String(amount) : "");
    setError(null);
    setIsEditing(true);
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    const parsed = Number(amountInput);
    if (amountInput.trim() === "" || Number.isNaN(parsed) || parsed < 0) {
      setError("Enter a valid, non-negative amount");
      return;
    }
    setError(null);
    setIsSaving(true);
    try {
      const result = await setTotalDebts(parsed);
      setAmount(result.amount);
      setIsEditing(false);
      showToast("Total debts saved", "success");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not save");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const result = await clearTotalDebts();
      setAmount(result.amount);
      setIsEditing(false);
      showToast("Total debts cleared", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not clear", "error");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold text-zinc-900">Total Debts</h2>
        {!isEditing && !isLoading && (
          <div className="flex items-center gap-2">
            <Button variant="ghost" className="!px-3 !py-1.5 text-xs" onClick={startEditing}>
              {amount !== null ? "Edit" : "Set value"}
            </Button>
            {amount !== null && (
              <Button variant="ghost" className="!px-3 !py-1.5 text-xs text-red-600 hover:text-red-700" onClick={handleDelete} isLoading={isDeleting}>
                Delete
              </Button>
            )}
          </div>
        )}
      </div>

      {isLoading ? (
        <Spinner size="sm" />
      ) : isEditing ? (
        <form onSubmit={handleSave} className="space-y-3">
          <TextField
            label="Total debts (IQD)"
            type="number"
            min={0}
            step="any"
            value={amountInput}
            onChange={(e) => setAmountInput(e.target.value)}
            error={error ?? undefined}
            autoFocus
          />
          <div className="flex gap-2">
            <Button type="submit" isLoading={isSaving}>
              Save
            </Button>
            <Button type="button" variant="secondary" onClick={() => setIsEditing(false)} disabled={isSaving}>
              Cancel
            </Button>
          </div>
        </form>
      ) : amount !== null ? (
        <p className="text-2xl font-bold text-zinc-900">{formatIQD(amount)}</p>
      ) : (
        <p className="text-sm text-zinc-500">No value set yet.</p>
      )}
    </div>
  );
}
