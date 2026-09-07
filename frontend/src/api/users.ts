import { api } from "@/api/client";
import type { Region, User, UserRole } from "@/types";

export interface CreateUserInput {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  region?: Region | null;
}

export interface UpdateUserInput {
  full_name?: string;
  email?: string;
  role?: UserRole;
  is_active?: boolean;
}

export function listUsers(): Promise<User[]> {
  return api.get<User[]>("/api/users");
}

export function getUser(id: string): Promise<User> {
  return api.get<User>(`/api/users/${id}`);
}

export function createUser(payload: CreateUserInput): Promise<User> {
  return api.post<User>("/api/users", payload);
}

export function updateUser(id: string, payload: UpdateUserInput): Promise<User> {
  return api.patch<User>(`/api/users/${id}`, payload);
}

export function deleteUser(id: string): Promise<void> {
  return api.delete<void>(`/api/users/${id}`);
}

/** Super Admin only. The backend re-checks `confirmUsername` against the
 * target account, so this is not merely a UI guard. */
/** Super Admin only: replace which regions an account may use. Granting opens
 * an empty wallet in that region; revoking leaves its history untouched. */
export function setUserRegions(id: string, regions: Region[]): Promise<User> {
  return api.put<User>(`/api/users/${id}/regions`, { regions });
}

export function permanentlyDeleteUser(id: string, confirmUsername: string): Promise<void> {
  return api.post<void>(`/api/users/${id}/permanent-delete`, { confirm_username: confirmUsername });
}

export interface MessageResponse {
  message: string;
}

export function changeOwnPassword(currentPassword: string, newPassword: string): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/users/me/password", { current_password: currentPassword, new_password: newPassword });
}

export function adminResetPassword(userId: string, newPassword: string): Promise<MessageResponse> {
  return api.post<MessageResponse>(`/api/users/${userId}/password`, { new_password: newPassword });
}
