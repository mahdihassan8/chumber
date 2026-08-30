import { api } from "@/api/client";
import type { User } from "@/types";

export function updateOwnProfile(payload: { full_name?: string; username?: string }): Promise<User> {
  return api.patch<User>("/api/users/me", payload);
}

export function listPredefinedAvatars(): Promise<string[]> {
  return api.get<string[]>("/api/profile/avatars");
}

export function selectAvatar(avatarUrl: string): Promise<User> {
  return api.post<User>("/api/profile/avatar/select", { avatar_url: avatarUrl });
}

export function uploadAvatar(file: File): Promise<User> {
  const formData = new FormData();
  formData.append("file", file);
  return api.postForm<User>("/api/profile/avatar/upload", formData);
}
