import type { ApiError } from "@/types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "chumber_token";

export class ApiRequestError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiRequestError";
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

const REGION_STORAGE_KEY = "chumber_region";

/** The region every request operates in, sent as X-Region. The backend always
 * re-validates it against the account's memberships, so this is a convenience
 * for the UI, never the security boundary. "all" is accepted from a Super Admin
 * only. */
export function getRegion(): string | null {
  return localStorage.getItem(REGION_STORAGE_KEY);
}

export function setRegion(region: string | null): void {
  if (region) {
    localStorage.setItem(REGION_STORAGE_KEY, region);
  } else {
    localStorage.removeItem(REGION_STORAGE_KEY);
  }
}

let onUnauthorized: (() => void) | null = null;
export function registerUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

function extractErrorMessage(body: unknown, fallback: string): string {
  const err = body as ApiError | undefined;
  if (!err || !err.detail) return fallback;
  if (typeof err.detail === "string") return err.detail;
  if (Array.isArray(err.detail)) {
    return err.detail.map((d) => d.msg).join(", ");
  }
  return fallback;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE" | "PUT";
  body?: unknown;
  isFormData?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, isFormData = false } = options;
  const token = getToken();

  const headers: Record<string, string> = {};
  if (!isFormData && body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const region = getRegion();
  if (region) {
    headers["X-Region"] = region;
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
  });

  if (response.status === 401) {
    setToken(null);
    onUnauthorized?.();
    throw new ApiRequestError(401, "Session expired. Please log in again.");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json") ? await response.json() : undefined;

  if (!response.ok) {
    throw new ApiRequestError(response.status, extractErrorMessage(data, "Something went wrong. Please try again."));
  }

  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, formData: FormData) => request<T>(path, { method: "POST", body: formData, isFormData: true }),
};

export { API_URL };
