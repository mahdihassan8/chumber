import { api } from "@/api/client";
import type { User, UserRole } from "@/types";

export interface CreateUserInput {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
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

export interface MessageResponse {
  message: string;
}

export function changeOwnPassword(currentPassword: string, newPassword: string): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/users/me/password", { current_password: currentPassword, new_password: newPassword });
}

export function adminResetPassword(userId: string, newPassword: string): Promise<MessageResponse> {
  return api.post<MessageResponse>(`/api/users/${userId}/password`, { new_password: newPassword });
}
