import { api } from "@/api/client";
import type { User } from "@/types";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export function login(username: string, password: string): Promise<TokenResponse> {
  return api.post<TokenResponse>("/api/auth/login", { username, password });
}

export function fetchMe(): Promise<User> {
  return api.get<User>("/api/auth/me");
}
