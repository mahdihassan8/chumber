import { useState, type FormEvent } from "react";
import { changeOwnPassword } from "@/api/users";
import { useToast } from "@/context/ToastContext";
import { TextField } from "@/components/common/TextField";
import { Button } from "@/components/common/Button";
import { ApiRequestError } from "@/api/client";

export function ChangePasswordForm() {
  const { showToast } = useToast();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const reset = () => {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New password and confirmation do not match");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await changeOwnPassword(currentPassword, newPassword);
      showToast(response.message, "success");
      reset();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not change password");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <TextField
        label="Current password"
        name="current_password"
        type="password"
        autoComplete="current-password"
        value={currentPassword}
        onChange={(e) => setCurrentPassword(e.target.value)}
        required
      />
      <TextField
        label="New password"
        name="new_password"
        type="password"
        autoComplete="new-password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        minLength={8}
        required
        hint="At least 8 characters."
      />
      <TextField
        label="Confirm new password"
        name="confirm_password"
        type="password"
        autoComplete="new-password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        minLength={8}
        required
      />
      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
          {error}
        </p>
      )}
      <Button type="submit" isLoading={isSubmitting}>
        Update password
      </Button>
    </form>
  );
}
