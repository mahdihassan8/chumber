import { useState, type FormEvent } from "react";
import { updateOwnProfile } from "@/api/profile";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { TextField } from "@/components/common/TextField";
import { Button } from "@/components/common/Button";
import { ApiRequestError } from "@/api/client";

export function ProfileCard() {
  const { user, setUser } = useAuth();
  const { showToast } = useToast();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [username, setUsername] = useState(user?.username ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!user) return null;

  const isDirty = fullName !== user.full_name || username !== user.username;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const updated = await updateOwnProfile({ full_name: fullName, username });
      setUser(updated);
      showToast("Profile updated", "success");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not update profile");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <TextField label="Full name" name="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} minLength={1} maxLength={150} required />
      <TextField label="Username" name="username" value={username} onChange={(e) => setUsername(e.target.value)} minLength={3} maxLength={50} required error={error ?? undefined} />
      <TextField label="Email" name="email" value={user.email} disabled hint="Contact an admin to change your email." />
      <Button type="submit" isLoading={isSubmitting} disabled={!isDirty}>
        Save changes
      </Button>
    </form>
  );
}
