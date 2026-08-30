import { api } from "@/api/client";
import type { Cart } from "@/types";

export function getCart(): Promise<Cart> {
  return api.get<Cart>("/api/cart");
}

export function addToCart(productId: string, quantity: number): Promise<Cart> {
  return api.post<Cart>("/api/cart/items", { product_id: productId, quantity });
}

export function updateCartItem(itemId: string, quantity: number): Promise<Cart> {
  return api.patch<Cart>(`/api/cart/items/${itemId}`, { quantity });
}

export function removeCartItem(itemId: string): Promise<Cart> {
  return api.delete<Cart>(`/api/cart/items/${itemId}`);
}
