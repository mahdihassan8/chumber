import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { User, UserRole } from "@/types";
import { adminResetPassword, createUser, updateUser } from "@/api/users";
import { useToast } from "@/context/ToastContext";
import { TextField } from "@/components/common/TextField";
import { Button } from "@/components/common/Button";
import { Modal } from "@/components/common/Modal";
import { ApiRequestError } from "@/api/client";

interface UserFormProps {
  existingUser?: User;
}

export function UserForm({ existingUser }: UserFormProps) {
  const isEdit = !!existingUser;
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [username, setUsername] = useState(existingUser?.username ?? "");
  const [email, setEmail] = useState(existingUser?.email ?? "");
  const [fullName, setFullName] = useState(existingUser?.full_name ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>(existingUser?.role ?? "customer");
  const [isActive, setIsActive] = useState(existingUser?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [showResetPassword, setShowResetPassword] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isResettingPassword, setIsResettingPassword] = useState(false);
  const [resetPasswordError, setResetPasswordError] = useState<string | null>(null);

  const handleResetPassword = async () => {
    if (!existingUser) return;
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
      const response = await adminResetPassword(existingUser.id, newPassword);
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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      if (isEdit && existingUser) {
        await updateUser(existingUser.id, { full_name: fullName, email, role, is_active: isActive });
        showToast("User updated", "success");
      } else {
        await createUser({ username, email, full_name: fullName, password, role });
        showToast("User created", "success");
      }
      navigate("/admin/users");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not save user");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card mx-auto max-w-lg space-y-4 p-6">
      <TextField
        label="Username"
        name="username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        disabled={isEdit}
        required
        minLength={3}
        maxLength={50}
      />
      <TextField label="Full name" name="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} required maxLength={150} />
      <TextField label="Email" name="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      {!isEdit && (
        <TextField
          label="Password"
          name="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          hint="At least 8 characters."
        />
      )}

      <div>
        <span className="label">Role</span>
        <div className="flex gap-2">
          {(["customer", "admin"] as UserRole[]).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRole(r)}
              className={`flex-1 rounded-lg border px-3 py-2.5 text-sm font-medium capitalize transition-colors ${
                role === r ? "border-brand-600 bg-brand-50 text-brand-700" : "border-zinc-200 text-zinc-600 hover:bg-zinc-50"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {isEdit && (
        <label className="flex items-center gap-2.5 text-sm font-medium text-zinc-700">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="h-4 w-4 rounded border-zinc-300 text-brand-600 focus:ring-brand-500" />
          Account active
        </label>
      )}

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
          {error}
        </p>
      )}

      <div className="flex gap-2 pt-2">
        <Button type="submit" isLoading={isSubmitting}>
          {isEdit ? "Save changes" : "Create user"}
        </Button>
        <Button type="button" variant="secondary" onClick={() => navigate("/admin/users")}>
          Cancel
        </Button>
        {isEdit && (
          <Button type="button" variant="secondary" onClick={() => setShowResetPassword(true)}>
            Reset password
          </Button>
        )}
      </div>

      {isEdit && existingUser && (
        <Modal isOpen={showResetPassword} onClose={() => setShowResetPassword(false)} title={`Reset password for ${existingUser.full_name}`} size="sm">
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
              <Button type="button" variant="secondary" onClick={() => setShowResetPassword(false)} disabled={isResettingPassword}>
                Cancel
              </Button>
              <Button type="button" onClick={handleResetPassword} isLoading={isResettingPassword}>
                Reset password
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </form>
  );
}
