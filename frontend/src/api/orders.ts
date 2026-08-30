import { api } from "@/api/client";
import type { CheckoutResponse, Order } from "@/types";

export function checkout(): Promise<CheckoutResponse> {
  return api.post<CheckoutResponse>("/api/orders/checkout");
}

export function getMyOrders(): Promise<Order[]> {
  return api.get<Order[]>("/api/users/me/orders");
}

export function getUserOrders(userId: string): Promise<Order[]> {
  return api.get<Order[]>(`/api/users/${userId}/orders`);
}

export function getAllOrders(): Promise<Order[]> {
  return api.get<Order[]>("/api/admin/orders");
}
