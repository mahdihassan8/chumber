import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { confirmAIProduct, draftAIProduct, rejectAIProduct } from "@/api/ai";
import type { AIProductDraft } from "@/types";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { useToast } from "@/context/ToastContext";
import { resolveAssetUrl } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

/** Checkerboard, so a transparent cut-out is visibly transparent rather than
 * looking like it has a white background. */
const CHECKERBOARD =
  "repeating-conic-gradient(#e4e4e7 0% 25%, #fafafa 0% 50%) 50% / 16px 16px";

export function AIProductCreatePage() {
  const [name, setName] = useState("");
  const [draft, setDraft] = useState<AIProductDraft | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Admin-editable review fields, seeded from what the AI extracted.
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editPrice, setEditPrice] = useState("");
  const [stock, setStock] = useState("");

  const { showToast } = useToast();
  const navigate = useNavigate();

  const search = async () => {
    if (!name.trim()) return;
    setIsSearching(true);
    setError(null);
    setDraft(null);
    try {
      const result = await draftAIProduct(name.trim());
      setDraft(result);
      if (result.status === "failed") {
        setError(result.error_message ?? "The AI could not find this product.");
        return;
      }
      setEditName(result.extracted_name ?? result.requested_name);
      setEditDescription(result.extracted_description ?? "");
      setEditPrice(result.suggested_price != null ? String(result.suggested_price) : "");
      setStock("");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not reach the AI assistant");
    } finally {
      setIsSearching(false);
    }
  };

  const confirm = async () => {
    if (!draft) return;
    const stockValue = Number(stock);
    if (!stock.trim() || Number.isNaN(stockValue) || stockValue < 0) {
      showToast("Enter a stock quantity first", "error");
      return;
    }
    setIsSaving(true);
    try {
      const result = await confirmAIProduct(draft.id, {
        stock_quantity: stockValue,
        name: editName.trim(),
        description: editDescription,
        price: editPrice.trim() === "" ? undefined : Number(editPrice),
      });
      showToast(`${editName.trim()} created`, "success");
      navigate(`/admin/products`, { state: { createdId: result.created_product_id } });
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not create the product", "error");
    } finally {
      setIsSaving(false);
    }
  };

  const discard = async () => {
    if (!draft) return;
    try {
      await rejectAIProduct(draft.id);
    } catch {
      // Discarding is a courtesy cleanup; the draft is harmless if it fails.
    }
    setDraft(null);
    setName("");
  };

  const previewSrc = resolveAssetUrl(draft?.staged_image_url ?? null);

  return (
    <div>
      <p className="mb-5 text-sm text-zinc-500">
        Enter a product name. The assistant looks it up, prepares a transparent image, and shows you everything before
        anything is saved.
      </p>

      <div className="card mb-6 flex flex-col gap-3 p-5 sm:flex-row sm:items-center">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="e.g. Snickers bar"
          className="input flex-1"
          disabled={isSearching}
          aria-label="Product name to look up"
        />
        <Button onClick={search} isLoading={isSearching} disabled={!name.trim()}>
          Find product
        </Button>
      </div>

      {isSearching && (
        <div className="space-y-4">
          <Skeleton className="h-64 w-full" />
          <p className="text-center text-sm text-zinc-500">Searching the web, fetching the image and removing its background…</p>
        </div>
      )}

      {!isSearching && error && <ErrorState message={error} onRetry={search} />}

      {!isSearching && draft && draft.status === "pending" && (
        <div className="space-y-5">
          <div className="card p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-zinc-900">Review before saving</p>
              <Badge color={draft.has_transparency ? "green" : "amber"}>
                {draft.has_transparency ? "Transparent PNG" : "No transparency — background kept"}
              </Badge>
            </div>

            <div className="flex flex-col gap-5 sm:flex-row">
              <div className="shrink-0">
                {previewSrc ? (
                  <img
                    src={previewSrc}
                    alt={draft.extracted_name ?? "Processed product"}
                    className="h-40 w-40 rounded-xl object-contain p-2"
                    style={{ background: CHECKERBOARD }}
                  />
                ) : (
                  <div className="flex h-40 w-40 items-center justify-center rounded-xl bg-zinc-100 text-xs text-zinc-400">
                    No image
                  </div>
                )}
                {draft.source_title && (
                  <p className="mt-2 max-w-40 truncate text-xs text-zinc-400" title={draft.source_url ?? undefined}>
                    Source: {draft.source_title}
                  </p>
                )}
              </div>

              <div className="flex-1 space-y-3">
                <label className="block">
                  <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-zinc-400">Name</span>
                  <input value={editName} onChange={(e) => setEditName(e.target.value)} className="input" />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-zinc-400">Description</span>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={2}
                    className="input resize-none"
                  />
                </label>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <label className="block">
                    <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-zinc-400">Price (IQD)</span>
                    <input
                      value={editPrice}
                      onChange={(e) => setEditPrice(e.target.value)}
                      inputMode="numeric"
                      className="input"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-zinc-400">
                      Stock quantity
                    </span>
                    <input
                      value={stock}
                      onChange={(e) => setStock(e.target.value)}
                      inputMode="numeric"
                      placeholder="Required"
                      className="input"
                      autoFocus
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>

          {draft.image_prompt && (
            <div className="card p-5">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-400">Generated image prompt</p>
              <p className="whitespace-pre-wrap text-sm text-zinc-600">{draft.image_prompt}</p>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={confirm} isLoading={isSaving}>
              Create product
            </Button>
            <Button variant="ghost" onClick={discard} disabled={isSaving}>
              Discard
            </Button>
            <p className="text-xs text-zinc-400">Nothing has been saved yet.</p>
          </div>
        </div>
      )}
    </div>
  );
}
