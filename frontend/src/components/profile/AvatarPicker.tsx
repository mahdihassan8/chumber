import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { listPredefinedAvatars, selectAvatar, uploadAvatar } from "@/api/profile";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { Avatar } from "@/components/common/Avatar";
import { Spinner } from "@/components/common/Spinner";
import { ApiRequestError } from "@/api/client";

export function AvatarPicker() {
  const { user, setUser } = useAuth();
  const { showToast } = useToast();
  const [avatars, setAvatars] = useState<string[]>([]);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listPredefinedAvatars()
      .then(setAvatars)
      .catch(() => setAvatars([]));
  }, []);

  if (!user) return null;

  const handleSelect = async (avatarUrl: string) => {
    setBusyKey(avatarUrl);
    try {
      const updated = await selectAvatar(avatarUrl);
      setUser(updated);
      showToast("Avatar updated", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not update avatar", "error");
    } finally {
      setBusyKey(null);
    }
  };

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusyKey("upload");
    try {
      const updated = await uploadAvatar(file);
      setUser(updated);
      showToast("Avatar uploaded", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not upload avatar", "error");
    } finally {
      setBusyKey(null);
      e.target.value = "";
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center gap-4">
        <Avatar src={user.avatar_url} name={user.full_name} size="xl" />
        <div>
          <button onClick={handleUploadClick} disabled={busyKey === "upload"} className="btn-secondary px-3.5 py-2 text-sm">
            {busyKey === "upload" ? <Spinner size="sm" /> : null}
            Upload photo
          </button>
          <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleFileChange} />
          <p className="mt-1.5 text-xs text-zinc-500">PNG, JPEG or WEBP. Max 5MB.</p>
        </div>
      </div>

      <p className="label">Or choose a predefined avatar</p>
      <div className="grid grid-cols-4 gap-3 sm:grid-cols-8">
        {avatars.map((avatarUrl) => (
          <button
            key={avatarUrl}
            onClick={() => handleSelect(avatarUrl)}
            disabled={busyKey === avatarUrl}
            className={`relative flex aspect-square items-center justify-center overflow-hidden rounded-full border-2 transition-all ${
              user.avatar_url === avatarUrl ? "border-brand-600 ring-2 ring-brand-200" : "border-transparent hover:border-zinc-200"
            }`}
          >
            {busyKey === avatarUrl ? <Spinner size="sm" /> : <img src={avatarUrl} alt="Predefined avatar" className="h-full w-full object-cover object-center" />}
          </button>
        ))}
      </div>
    </div>
  );
}
