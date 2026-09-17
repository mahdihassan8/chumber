import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { confirmAIProduct, draftAIProduct, rejectAIProduct, retryAIProductImage } from "@/api/ai";
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

/** Advanced on a timer rather than from real backend events: the draft call is
 * a single request, so these are an honest description of the stages the
 * server goes through, not a live progress feed. The final state always comes
 * from the response. */
const PROGRESS_STEPS = [
  "Looking up the product…",
  "Searching for a real product image…",
  "Applying the GTA style…",
  "Removing the background…",
  "Uploading the image…",
];
const STEP_MS = 2500;

/** What the admin is told for each image outcome. Only "ok" means an image was
 * stored — every other state says so plainly rather than implying one exists. */
const IMAGE_STATUS_TEXT: Record<string, { label: string; tone: "green" | "amber" | "zinc" }> = {
  ok: { label: "Image ready", tone: "green" },
  not_configured: { label: "Image search not configured", tone: "zinc" },
  search_failed: { label: "Image search failed", tone: "amber" },
  no_results: { label: "No product image found", tone: "amber" },
  fetch_failed: { label: "Found images could not be downloaded", tone: "amber" },
  processing_failed: { label: "Image processing failed", tone: "amber" },
  not_attempted: { label: "No image", tone: "zinc" },
};

export function AIProductCreatePage() {
  const [name, setName] = useState("");
  const [draft, setDraft] = useState<AIProductDraft | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
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
    setProgressStep(0);
    // Stops short of the last step so it never claims to have finished before
    // the response actually lands.
    const ticker = setInterval(
      () => setProgressStep((s) => Math.min(s + 1, PROGRESS_STEPS.length - 1)),
      STEP_MS
    );
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
      clearInterval(ticker);
      setIsSearching(false);
    }
  };

  const retryImage = async () => {
    if (!draft) return;
    setIsRetrying(true);
    try {
      const updated = await retryAIProductImage(draft.id);
      setDraft(updated);
      showToast(updated.image_status === "ok" ? "Image ready" : "Still no usable image", updated.image_status === "ok" ? "success" : "error");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not retry the image", "error");
    } finally {
      setIsRetrying(false);
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
          <ol className="space-y-1.5 text-center text-sm text-zinc-500">
            {PROGRESS_STEPS.map((label, i) => (
              <li key={label} className={i === progressStep ? "font-medium text-zinc-900" : ""}>
                {i < progressStep ? "✓ " : ""}
                {label}
              </li>
            ))}
          </ol>
        </div>
      )}

      {!isSearching && error && <ErrorState message={error} onRetry={search} />}

      {!isSearching && draft && draft.status === "pending" && (
        <div className="space-y-5">
          <div className="card p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-zinc-900">Review before saving</p>
              <div className="flex flex-wrap items-center gap-2">
                <Badge color={IMAGE_STATUS_TEXT[draft.image_status]?.tone ?? "zinc"}>
                  {IMAGE_STATUS_TEXT[draft.image_status]?.label ?? draft.image_status}
                </Badge>
                {draft.image_status === "ok" && !draft.has_transparency && (
                  <Badge color="amber">Background kept</Badge>
                )}
                {draft.image_status !== "ok" && (
                  <Button
                    variant="ghost"
                    className="px-2.5 py-1 text-xs"
                    isLoading={isRetrying}
                    onClick={retryImage}
                  >
                    Retry image
                  </Button>
                )}
              </div>
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
                {draft.source_url && (
                  <p className="mt-2 max-w-40 truncate text-xs text-zinc-400" title={draft.source_url}>
                    Source: {draft.source_title || new URL(draft.source_url).hostname}
                  </p>
                )}
                {draft.image_error && (
                  <p className="mt-1 max-w-40 text-xs text-amber-700">{draft.image_error}</p>
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
