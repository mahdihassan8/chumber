import { useState } from "react";
import type { AIRestockRequest } from "@/types";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { confirmRestockRequest, rejectRestockRequest } from "@/api/ai";
import { useToast } from "@/context/ToastContext";
import { formatDateTime } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

const STATUS_BADGE: Record<AIRestockRequest["status"], { color: "green" | "red" | "amber" | "zinc"; label: string }> = {
  pending: { color: "amber", label: "Awaiting confirmation" },
  confirmed: { color: "green", label: "Confirmed" },
  rejected: { color: "zinc", label: "Rejected" },
  failed: { color: "red", label: "Could not process" },
};

interface ProposedActionCardProps {
  request: AIRestockRequest;
  onUpdated: (updated: AIRestockRequest) => void;
}

export function ProposedActionCard({ request, onUpdated }: ProposedActionCardProps) {
  const { showToast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState<"confirm" | "reject" | null>(null);
  const status = STATUS_BADGE[request.status];

  const handleConfirm = async () => {
    setIsSubmitting("confirm");
    try {
      const updated = await confirmRestockRequest(request.id);
      onUpdated(updated);
      showToast(`Restocked ${updated.resolved_product_name} (+${updated.parsed_quantity})`, "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not confirm restock", "error");
    } finally {
      setIsSubmitting(null);
    }
  };

  const handleReject = async () => {
    setIsSubmitting("reject");
    try {
      const updated = await rejectRestockRequest(request.id);
      onUpdated(updated);
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not reject request", "error");
    } finally {
      setIsSubmitting(null);
    }
  };

  return (
    <div className="card animate-fade-in space-y-3 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-zinc-400">{formatDateTime(request.created_at)}</p>
          <p className="mt-0.5 text-sm text-zinc-700">
            {request.input_type === "voice" ? "🎙️ " : ""}"{request.raw_input}"
          </p>
        </div>
        <Badge color={status.color}>{status.label}</Badge>
      </div>

      {request.status === "failed" ? (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{request.error_message}</p>
      ) : (
        <div className="rounded-lg bg-zinc-50 p-3">
          <p className="text-sm text-zinc-600">
            Restock <span className="font-semibold text-zinc-900">{request.resolved_product_name ?? request.parsed_product_name}</span> by{" "}
            <span className="font-semibold text-zinc-900">{request.parsed_quantity}</span> units
          </p>
          {request.resolved_product_id ? (
            <p className="mt-1 text-xs text-zinc-500">Current stock: {request.current_stock} → new stock: {(request.current_stock ?? 0) + (request.parsed_quantity ?? 0)}</p>
          ) : (
            <p className="mt-1 text-xs font-medium text-red-600">No matching product found in the catalog. Add the product first or rephrase.</p>
          )}
        </div>
      )}

      {request.status === "pending" && (
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={handleReject} isLoading={isSubmitting === "reject"} disabled={!!isSubmitting}>
            Reject
          </Button>
          <Button onClick={handleConfirm} isLoading={isSubmitting === "confirm"} disabled={!!isSubmitting || !request.resolved_product_id}>
            Confirm restock
          </Button>
        </div>
      )}
    </div>
  );
}
