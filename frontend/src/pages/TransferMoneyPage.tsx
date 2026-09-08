import { useEffect, useState, type FormEvent } from "react";
import { listTransferRecipients, sendTransfer, getMyTransferHistory } from "@/api/transfers";
import type { Transfer, TransferRecipient } from "@/types";
import { PageContainer } from "@/components/layout/PageContainer";
import { RecipientList } from "@/components/transfer/RecipientList";
import { TransferHistoryList } from "@/components/transfer/TransferHistoryList";
import { Avatar } from "@/components/common/Avatar";
import { Button } from "@/components/common/Button";
import { TextField } from "@/components/common/TextField";
import { ErrorState } from "@/components/common/ErrorState";
import { BeansAmount } from "@/components/common/BeansAmount";
import { useAuth } from "@/context/AuthContext";
import { useBalance } from "@/context/BalanceContext";
import { useRegion } from "@/context/RegionContext";
import { useToast } from "@/context/ToastContext";
import { formatBeans, IQD_PER_BEAN } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

type Tab = "send" | "history";

export function TransferMoneyPage() {
  const { user } = useAuth();
  const { current } = useRegion();
  const { showToast } = useToast();
  // Shared with the navbar/profile balance display -- calling refresh() here
  // after a successful transfer updates the sender's balance everywhere
  // immediately, with no page reload needed.
  const { balance, refresh: refreshBalance } = useBalance();

  const [tab, setTab] = useState<Tab>("send");

  const [recipients, setRecipients] = useState<TransferRecipient[]>([]);
  const [recipientsLoading, setRecipientsLoading] = useState(true);
  const [recipientsError, setRecipientsError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TransferRecipient | null>(null);

  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  const [history, setHistory] = useState<Transfer[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const loadRecipients = () => {
    setRecipientsLoading(true);
    setRecipientsError(null);
    listTransferRecipients()
      .then(setRecipients)
      .catch((err) => setRecipientsError(err instanceof ApiRequestError ? err.message : "Could not load recipients"))
      .finally(() => setRecipientsLoading(false));
  };

  const loadHistory = () => {
    setHistoryLoading(true);
    setHistoryError(null);
    getMyTransferHistory()
      .then(setHistory)
      .catch((err) => setHistoryError(err instanceof ApiRequestError ? err.message : "Could not load transfer history"))
      .finally(() => setHistoryLoading(false));
  };

  useEffect(() => {
    loadRecipients();
    loadHistory();
    setSelected(null);
    // Balance itself is shared global state (BalanceContext) and already
    // re-fetches on its own when the region changes -- nothing to trigger here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current]);

  const resetForm = () => {
    setAmount("");
    setNote("");
    setFormError(null);
  };

  const handleSelect = (r: TransferRecipient) => {
    setSelected(r);
    resetForm();
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected) return;

    const beans = Number(amount);
    if (!amount.trim() || !Number.isInteger(beans) || beans <= 0) {
      setFormError("Enter a whole number of Beans greater than 0");
      return;
    }
    const iqd = beans * IQD_PER_BEAN;
    // A friendly, non-authoritative check -- the backend re-validates the
    // real balance itself and is what actually enforces this.
    if (balance !== null && iqd > balance) {
      setFormError("You don't have enough balance for this transfer");
      return;
    }

    setFormError(null);
    setIsSending(true);
    try {
      await sendTransfer(selected.id, iqd, note.trim() || null);
      showToast(`Sent ${formatBeans(iqd)} Beans to ${selected.full_name}`, "success");
      resetForm();
      setSelected(null);
      // Immediate, no-refresh updates: the sender's balance (everywhere it's
      // shown, including the navbar) and their own transfer history.
      refreshBalance();
      loadHistory();
    } catch (err) {
      setFormError(err instanceof ApiRequestError ? err.message : "Could not send transfer");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <PageContainer className="max-w-3xl">
      <h1 className="mb-1 text-2xl font-bold text-zinc-900">Transfer Money</h1>
      <p className="mb-6 text-sm text-zinc-500">Send Beans directly to another user in your region.</p>

      <div className="mb-6 flex gap-1 rounded-lg bg-zinc-100 p-1">
        <button
          onClick={() => setTab("send")}
          className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            tab === "send" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700"
          }`}
        >
          Send
        </button>
        <button
          onClick={() => setTab("history")}
          className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            tab === "history" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700"
          }`}
        >
          History
        </button>
      </div>

      {tab === "send" ? (
        recipientsError ? (
          <ErrorState message={recipientsError} onRetry={loadRecipients} />
        ) : !selected ? (
          <RecipientList recipients={recipients} isLoading={recipientsLoading} onSelect={handleSelect} />
        ) : (
          <div className="card p-5">
            <button onClick={() => setSelected(null)} className="mb-4 flex items-center gap-1.5 text-sm font-medium text-zinc-500 hover:text-zinc-700">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
              </svg>
              Choose a different recipient
            </button>

            <div className="mb-5 flex items-center gap-3">
              <Avatar src={selected.avatar_url} name={selected.full_name} size="lg" />
              <div>
                <p className="font-semibold text-zinc-900">{selected.full_name}</p>
                <p className="text-sm text-zinc-500">@{selected.username}</p>
              </div>
            </div>

            <div className="mb-5 rounded-lg bg-zinc-50 px-4 py-3">
              <p className="text-xs text-zinc-500">Your balance</p>
              <p className="text-lg font-bold text-zinc-900">{balance !== null ? <BeansAmount amount={balance} /> : "—"}</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <TextField
                label="Amount (Beans)"
                type="number"
                min={1}
                step={1}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="e.g. 10"
                autoFocus
              />
              <TextField label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} placeholder="What's this for?" maxLength={500} />
              {formError && <p className="text-sm font-medium text-red-600">{formError}</p>}
              <Button type="submit" fullWidth isLoading={isSending}>
                Transfer
              </Button>
            </form>
          </div>
        )
      ) : historyError ? (
        <ErrorState message={historyError} onRetry={loadHistory} />
      ) : (
        <TransferHistoryList transfers={history} isLoading={historyLoading} currentUserId={user?.id} />
      )}
    </PageContainer>
  );
}
