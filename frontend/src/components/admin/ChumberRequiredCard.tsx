import { useEffect, useState, type FormEvent } from "react";
import { clearChumberRequired, getChumberRequired, setChumberRequired } from "@/api/admin";
import { useToast } from "@/context/ToastContext";
import { ApiRequestError } from "@/api/client";
import { TextField } from "@/components/common/TextField";
import { Button } from "@/components/common/Button";
import { Spinner } from "@/components/common/Spinner";
import { formatIQD } from "@/utils/assets";

/** Admin Dashboard section for the current region's "Chumber required"
 * figure: a single editable amount + optional note, persisted server-side.
 * Deleting only clears the value/note back to empty — the section and its
 * input stay right here, ready for a new value. */
export function ChumberRequiredCard() {
  const { showToast } = useToast();
  const [amount, setAmount] = useState<number | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [amountInput, setAmountInput] = useState("");
  const [noteInput, setNoteInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const load = () => {
    setIsLoading(true);
    getChumberRequired()
      .then((r) => {
        setAmount(r.amount);
        setNote(r.note);
      })
      .catch((err) => showToast(err instanceof ApiRequestError ? err.message : "Could not load Chumber required", "error"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const startEditing = () => {
    setAmountInput(amount !== null ? String(amount) : "");
    setNoteInput(note ?? "");
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
      const result = await setChumberRequired(parsed, noteInput.trim() || null);
      setAmount(result.amount);
      setNote(result.note);
      setIsEditing(false);
      showToast("Chumber required saved", "success");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not save");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const result = await clearChumberRequired();
      setAmount(result.amount);
      setNote(result.note);
      setIsEditing(false);
      showToast("Chumber required cleared", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not clear", "error");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold text-zinc-900">Chumber Required</h2>
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
            label="Amount (IQD)"
            type="number"
            min={0}
            step="any"
            value={amountInput}
            onChange={(e) => setAmountInput(e.target.value)}
            error={error ?? undefined}
            autoFocus
          />
          <div>
            <label className="label">Note (optional)</label>
            <textarea
              className="input min-h-[72px] resize-y"
              value={noteInput}
              onChange={(e) => setNoteInput(e.target.value)}
              maxLength={1000}
              placeholder="Optional context for this figure"
            />
          </div>
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
        <div>
          <p className="text-2xl font-bold text-zinc-900">{formatIQD(amount)}</p>
          {note && <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-500">{note}</p>}
        </div>
      ) : (
        <p className="text-sm text-zinc-500">No value set yet.</p>
      )}
    </div>
  );
}
