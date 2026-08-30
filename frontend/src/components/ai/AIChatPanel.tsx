import { useState, type FormEvent } from "react";
import type { AIRestockRequest } from "@/types";
import { parseRestockMessage } from "@/api/ai";
import { VoiceInputButton } from "@/components/ai/VoiceInputButton";
import { ProposedActionCard } from "@/components/ai/ProposedActionCard";
import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/common/ErrorState";
import { useToast } from "@/context/ToastContext";
import { ApiRequestError } from "@/api/client";

const EXAMPLES = ["Add 20 Coca Cola", "Restock Coca Cola with 30 units", "Add fifteen bottles of Sprite"];

interface AIChatPanelProps {
  requests: AIRestockRequest[];
  onNewRequest: (request: AIRestockRequest) => void;
  onUpdated: (request: AIRestockRequest) => void;
}

export function AIChatPanel({ requests, onNewRequest, onUpdated }: AIChatPanelProps) {
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { showToast } = useToast();

  const submitMessage = async (text: string, inputType: "text" | "voice") => {
    if (!text.trim() || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const request = await parseRestockMessage(text.trim(), inputType);
      onNewRequest(request);
      setMessage("");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not process request", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submitMessage(message, "text");
  };

  return (
    <div className="space-y-5">
      <form onSubmit={handleSubmit} className="card flex items-center gap-2 p-3">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder='Try "Add 20 Coca Cola"...'
          className="input flex-1 border-none shadow-none focus:ring-0"
          disabled={isSubmitting}
        />
        <VoiceInputButton onTranscript={(text) => submitMessage(text, "voice")} disabled={isSubmitting} />
        <Button type="submit" isLoading={isSubmitting} disabled={!message.trim()}>
          Send
        </Button>
      </form>

      {requests.length === 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-zinc-400">Try:</span>
          {EXAMPLES.map((ex) => (
            <button key={ex} onClick={() => setMessage(ex)} className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-200">
              {ex}
            </button>
          ))}
        </div>
      )}

      {requests.length === 0 ? (
        <EmptyState title="No restock requests yet" description="Type a message above or use voice input to get started." />
      ) : (
        <div className="space-y-3">
          {requests.map((request) => (
            <ProposedActionCard key={request.id} request={request} onUpdated={onUpdated} />
          ))}
        </div>
      )}
    </div>
  );
}
