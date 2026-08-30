import { api } from "@/api/client";
import type { Product } from "@/types";

export interface ProductInput {
  name: string;
  description: string;
  price: number;
  stock_quantity: number;
  image_url?: string | null;
  is_active?: boolean;
}

export function listProducts(): Promise<Product[]> {
  return api.get<Product[]>("/api/products");
}

export function getProduct(id: string): Promise<Product> {
  return api.get<Product>(`/api/products/${id}`);
}

export function createProduct(payload: ProductInput): Promise<Product> {
  return api.post<Product>("/api/products", payload);
}

export function updateProduct(id: string, payload: Partial<ProductInput>): Promise<Product> {
  return api.patch<Product>(`/api/products/${id}`, payload);
}

export function deleteProduct(id: string): Promise<void> {
  return api.delete<void>(`/api/products/${id}`);
}

export function restockProduct(id: string, quantity: number): Promise<Product> {
  return api.post<Product>(`/api/products/${id}/restock`, { quantity });
}

export function uploadProductImage(id: string, file: File): Promise<Product> {
  const formData = new FormData();
  formData.append("file", file);
  return api.postForm<Product>(`/api/products/${id}/image`, formData);
}
