import { useState } from "react";
import { Link } from "react-router-dom";
import type { Balance, User } from "@/types";
import { getUserBalance, addUserBalance, subtractUserBalance } from "@/api/balance";
import { Avatar } from "@/components/common/Avatar";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { Modal } from "@/components/common/Modal";
import { TextField } from "@/components/common/TextField";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { BalanceBreakdown } from "@/components/balance/BalanceBreakdown";
import { TransactionList } from "@/components/balance/TransactionList";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { formatIQD, toBeans } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

interface UserBalanceRowProps {
  user: User;
  onBalanceChanged: (userId: string, newBalance: number) => void;
}

type BalanceModalMode = "add" | "subtract" | null;

export function UserBalanceRow({ user, onBalanceChanged }: UserBalanceRowProps) {
  const { showToast } = useToast();
  const { user: authUser, setUser: setAuthUser } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<Balance | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalMode, setModalMode] = useState<BalanceModalMode>(null);
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadDetail = () => {
    setIsLoading(true);
    setError(null);
    getUserBalance(user.id)
      .then(setDetail)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load balance details"))
      .finally(() => setIsLoading(false));
  };

  const toggleExpanded = () => {
    const next = !expanded;
    setExpanded(next);
    if (next && !detail) loadDetail();
  };

  const closeModal = () => {
    setModalMode(null);
    setAmount("");
    setDescription("");
    setFormError(null);
  };

  const handleSubmitBalanceChange = async () => {
    const value = Number(amount);
    if (!value || value <= 0) {
      setFormError("Enter an amount greater than 0");
      return;
    }
    // 250 IQD increments only — mirrors the backend's multiple_of=250
    // validation, and keeps the customer's Beans balance a whole number.
    if (value % 250 !== 0) {
      setFormError("Amount must be in increments of 250 IQD (1 Bean)");
      return;
    }
    setFormError(null);
    setIsSubmitting(true);
    try {
      const updated =
        modalMode === "subtract"
          ? await subtractUserBalance(user.id, value, description || undefined)
          : await addUserBalance(user.id, value, description || undefined);
      setDetail(updated);
      onBalanceChanged(user.id, updated.balance);
      // An admin can recharge/deduct their own account (Admin = Customer too)
      // — when that's who this row is for, the navbar/profile balance reads
      // from AuthContext, not this page's local state, so it needs its own
      // update or it'd stay stale until a manual refresh.
      if (authUser?.id === user.id) setAuthUser({ ...authUser, balance: updated.balance });
      showToast(
        `${modalMode === "subtract" ? "Subtracted" : "Added"} ${formatIQD(value)} ${modalMode === "subtract" ? "from" : "to"} ${user.full_name}`,
        "success"
      );
      closeModal();
    } catch (err) {
      setFormError(err instanceof ApiRequestError ? err.message : `Could not ${modalMode === "subtract" ? "subtract" : "add"} balance`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 p-4">
        <button onClick={toggleExpanded} className="flex flex-1 items-center gap-3 text-left" aria-expanded={expanded}>
          <svg className={`h-4 w-4 shrink-0 text-zinc-400 transition-transform ${expanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
          <Avatar src={user.avatar_url} name={user.full_name} size="sm" />
          <div className="min-w-0">
            <Link
              to={`/admin/users/${user.id}`}
              onClick={(e) => e.stopPropagation()}
              className="truncate font-medium text-zinc-900 hover:text-brand-700 hover:underline"
            >
              {user.full_name}
            </Link>
            <p className="truncate text-xs text-zinc-500">@{user.username}</p>
          </div>
          <Badge color={user.role === "admin" ? "blue" : "zinc"}>{user.role}</Badge>
        </button>
        <span className="font-bold text-zinc-900">{formatIQD(user.balance)}</span>
        <Button variant="secondary" className="px-3 py-1.5 text-xs" onClick={() => setModalMode("add")}>
          + Add balance
        </Button>
        <Button variant="secondary" className="px-3 py-1.5 text-xs" onClick={() => setModalMode("subtract")}>
          − Subtract balance
        </Button>
      </div>

      {expanded && (
        <div className="border-t border-zinc-100 bg-zinc-50/50 p-4">
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : error ? (
            <ErrorState message={error} onRetry={loadDetail} />
          ) : detail ? (
            <div className="space-y-4">
              <BalanceBreakdown totalReceived={detail.total_received} totalSpent={detail.total_spent} balance={detail.balance} />
              <div>
                <p className="mb-1.5 text-sm font-semibold text-zinc-900">Transaction History</p>
                <div className="card px-4">
                  <TransactionList transactions={detail.transactions} />
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}

      <Modal
        isOpen={modalMode !== null}
        onClose={closeModal}
        title={`${modalMode === "subtract" ? "Subtract balance from" : "Add balance to"} ${user.full_name}`}
        size="sm"
      >
        <div className="space-y-4">
          <TextField
            label="Amount (IQD)"
            name="amount"
            type="number"
            min="250"
            step="250"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            hint={Number(amount) > 0 ? `= ${toBeans(Number(amount)).toLocaleString()} Beans for the customer` : "250 IQD = 1 Bean"}
            autoFocus
          />
          <TextField label="Description (optional)" name="description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Monthly top-up" />
          {formError && <p className="text-sm font-medium text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeModal} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant={modalMode === "subtract" ? "danger" : "primary"} onClick={handleSubmitBalanceChange} isLoading={isSubmitting}>
              {modalMode === "subtract" ? "Subtract balance" : "Add balance"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
