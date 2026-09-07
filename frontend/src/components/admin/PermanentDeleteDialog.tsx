import { useEffect, useState } from "react";
import type { User } from "@/types";
import { Modal } from "@/components/common/Modal";
import { Button } from "@/components/common/Button";
import { TextField } from "@/components/common/TextField";

interface PermanentDeleteDialogProps {
  /** The account to erase; null closes the dialog. */
  user: User | null;
  onConfirm: (confirmUsername: string) => Promise<void>;
  onCancel: () => void;
}

/** Super-Admin-only confirmation for an irreversible account purge. The typed
 * username is a deliberate speed bump, not the security boundary — the backend
 * re-checks it (see user_service.permanently_delete_user). */
export function PermanentDeleteDialog({ user, onConfirm, onCancel }: PermanentDeleteDialogProps) {
  const [typed, setTyped] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Clear the box whenever a different account is targeted, so a previously
  // typed name can never carry over to the next victim.
  useEffect(() => setTyped(""), [user?.id]);

  const matches = user !== null && typed === user.username;

  const handleConfirm = async () => {
    if (!matches) return;
    setIsSubmitting(true);
    try {
      await onConfirm(typed);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={user !== null} onClose={onCancel} title="Permanently Delete Account" size="sm">
      <div className="space-y-4">
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2">
          <p className="text-xs font-medium text-red-700">Username</p>
          <p className="font-semibold text-red-900">{user?.username}</p>
        </div>

        <div className="text-sm text-zinc-600">
          <p className="font-semibold text-zinc-900">This action is permanent and cannot be undone.</p>
          <p className="mt-1">It will permanently delete this account and all data belonging to it, including:</p>
          <ul className="mt-2 list-inside list-disc space-y-0.5">
            <li>Balance</li>
            <li>Transactions</li>
            <li>Orders</li>
            <li>Purchases</li>
            <li>Related user data</li>
          </ul>
        </div>

        <TextField
          label={`To confirm, type the username exactly: ${user?.username ?? ""}`}
          name="confirm_username"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder={user?.username}
          autoComplete="off"
          autoFocus
        />

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleConfirm} disabled={!matches} isLoading={isSubmitting}>
            Delete Permanently
          </Button>
        </div>
      </div>
    </Modal>
  );
}
