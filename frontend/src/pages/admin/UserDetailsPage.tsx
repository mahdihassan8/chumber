import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getUser, adminResetPassword } from "@/api/users";
import { getUserBalance, addUserBalance, subtractUserBalance } from "@/api/balance";
import { getUserOrders } from "@/api/orders";
import type { Balance, Currency, Order, User } from "@/types";
import { Avatar } from "@/components/common/Avatar";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { TextField } from "@/components/common/TextField";
import { Modal } from "@/components/common/Modal";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { OrderList } from "@/components/orders/OrderList";
import { BalanceBreakdown } from "@/components/balance/BalanceBreakdown";
import { TransactionList } from "@/components/balance/TransactionList";
import { CurrencySwitcher } from "@/components/balance/CurrencySwitcher";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { formatByCurrency } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

type BalanceModalMode = "add" | "subtract" | null;

export function UserDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const { showToast } = useToast();
  const { user: authUser, setUser: setAuthUser } = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [balance, setBalance] = useState<Balance | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [balanceModalMode, setBalanceModalMode] = useState<BalanceModalMode>(null);
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isResettingPassword, setIsResettingPassword] = useState(false);
  const [resetPasswordError, setResetPasswordError] = useState<string | null>(null);

  const load = () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    Promise.all([getUser(id), getUserBalance(id), getUserOrders(id)])
      .then(([u, b, o]) => {
        setUser(u);
        setBalance(b);
        setOrders(o);
      })
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load user"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, [id]);

  const closeBalanceModal = () => {
    setBalanceModalMode(null);
    setAmount("");
    setDescription("");
    setFormError(null);
  };

  const handleCurrencyChanged = (newCurrency: Currency, newBalance: number) => {
    setBalance((prev) => (prev ? { ...prev, currency: newCurrency, balance: newBalance } : prev));
    setUser((prev) => (prev ? { ...prev, currency: newCurrency, balance: newBalance } : prev));
    if (authUser && authUser.id === id) setAuthUser({ ...authUser, currency: newCurrency, balance: newBalance });
  };

  const handleSubmitBalanceChange = async () => {
    if (!id) return;
    const value = Number(amount);
    if (!value || value <= 0) {
      setFormError("Enter an amount greater than 0");
      return;
    }
    // Quarter increments only — mirrors the backend's multiple_of=0.25
    // validation. Multiplying by 4 sidesteps float precision issues since
    // 0.25 is exactly representable in binary.
    if (Math.round(value * 4) !== value * 4) {
      setFormError("Amount must be in increments of 0.25");
      return;
    }
    setFormError(null);
    setIsSubmitting(true);
    try {
      const updatedBalance =
        balanceModalMode === "subtract"
          ? await subtractUserBalance(id, value, description || undefined)
          : await addUserBalance(id, value, description || undefined);
      setBalance(updatedBalance);
      setUser((prev) => (prev ? { ...prev, balance: updatedBalance.balance } : prev));
      // Viewing your own admin account's detail page and recharging/deducting
      // it is a valid path (Admin = Customer too) — keep the navbar/profile
      // balance, which reads from AuthContext, in sync too.
      if (authUser?.id === id) setAuthUser({ ...authUser, balance: updatedBalance.balance });
      showToast(
        `${balanceModalMode === "subtract" ? "Subtracted" : "Added"} ${formatByCurrency(value, updatedBalance.currency)} ${balanceModalMode === "subtract" ? "from" : "to"} ${user?.full_name}`,
        "success"
      );
      closeBalanceModal();
    } catch (err) {
      setFormError(err instanceof ApiRequestError ? err.message : `Could not ${balanceModalMode === "subtract" ? "subtract" : "add"} balance`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetPassword = async () => {
    if (!id) return;
    if (newPassword.length < 8) {
      setResetPasswordError("Password must be at least 8 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      setResetPasswordError("Password and confirmation do not match");
      return;
    }
    setResetPasswordError(null);
    setIsResettingPassword(true);
    try {
      const response = await adminResetPassword(id, newPassword);
      showToast(response.message, "success");
      setShowResetPassword(false);
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setResetPasswordError(err instanceof ApiRequestError ? err.message : "Could not reset password");
    } finally {
      setIsResettingPassword(false);
    }
  };

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error || !user) return <ErrorState message={error ?? "User not found"} onRetry={load} />;

  return (
    <div className="space-y-6">
      <Link to="/admin/users" className="inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-800">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to users
      </Link>

      <div className="card flex flex-col gap-4 p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <Avatar src={user.avatar_url} name={user.full_name} size="lg" />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-zinc-900">{user.full_name}</h1>
                <Badge color={user.role === "admin" ? "blue" : "zinc"}>{user.role}</Badge>
                <Badge color={user.is_active ? "green" : "red"}>{user.is_active ? "Active" : "Inactive"}</Badge>
              </div>
              <p className="text-sm text-zinc-500">
                @{user.username} · {user.email}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-zinc-500">Currency</span>
              <CurrencySwitcher userId={user.id} currency={balance?.currency ?? user.currency} onChanged={handleCurrencyChanged} />
            </div>
            <Button onClick={() => setBalanceModalMode("add")}>+ Add balance</Button>
            <Button variant="secondary" onClick={() => setBalanceModalMode("subtract")}>
              − Subtract balance
            </Button>
            <Button variant="secondary" onClick={() => setShowResetPassword(true)}>
              Reset password
            </Button>
            <Link to={`/admin/users/${user.id}/edit`} className="btn-secondary px-4 py-2.5 text-sm">
              Edit
            </Link>
          </div>
        </div>

        {balance && (
          <BalanceBreakdown totalReceived={balance.total_received} totalSpent={balance.total_spent} balance={balance.balance} currency={balance.currency} />
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 font-semibold text-zinc-900">Purchase History</h2>
          <OrderList orders={orders} />
        </section>
        <section>
          <h2 className="mb-3 font-semibold text-zinc-900">Balance Transactions</h2>
          <div className="card p-4">
            <TransactionList transactions={balance?.transactions ?? []} />
          </div>
        </section>
      </div>

      <Modal
        isOpen={balanceModalMode !== null}
        onClose={closeBalanceModal}
        title={`${balanceModalMode === "subtract" ? "Subtract balance from" : "Add balance to"} ${user.full_name}`}
        size="sm"
      >
        <div className="space-y-4">
          <TextField
            label={`Amount (${balance?.currency ?? user.currency})`}
            name="amount"
            type="number"
            min="0.25"
            step="0.25"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            autoFocus
          />
          <TextField label="Description (optional)" name="description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Monthly top-up" />
          {formError && <p className="text-sm font-medium text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeBalanceModal} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant={balanceModalMode === "subtract" ? "danger" : "primary"} onClick={handleSubmitBalanceChange} isLoading={isSubmitting}>
              {balanceModalMode === "subtract" ? "Subtract balance" : "Add balance"}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showResetPassword} onClose={() => setShowResetPassword(false)} title={`Reset password for ${user.full_name}`} size="sm">
        <div className="space-y-4">
          <TextField
            label="New password"
            name="new_password"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={8}
            hint="At least 8 characters."
            autoFocus
          />
          <TextField
            label="Confirm new password"
            name="confirm_password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            minLength={8}
          />
          {resetPasswordError && <p className="text-sm font-medium text-red-600">{resetPasswordError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowResetPassword(false)} disabled={isResettingPassword}>
              Cancel
            </Button>
            <Button onClick={handleResetPassword} isLoading={isResettingPassword}>
              Reset password
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
