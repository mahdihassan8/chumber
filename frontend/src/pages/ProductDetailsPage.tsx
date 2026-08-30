import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getProduct } from "@/api/products";
import type { Product } from "@/types";
import { PageContainer } from "@/components/layout/PageContainer";
import { ProductImage } from "@/components/product/ProductImage";
import { StockBadge } from "@/components/product/StockBadge";
import { QuantitySelector } from "@/components/product/QuantitySelector";
import { Button } from "@/components/common/Button";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { useCart } from "@/context/CartContext";
import { formatBeans } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

export function ProductDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addItem, mutatingItemId, getSelectedQuantity, setSelectedQuantity } = useCart();
  const [product, setProduct] = useState<Product | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    getProduct(id)
      .then(setProduct)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Product not found"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, [id]);

  if (isLoading) {
    return (
      <PageContainer>
        <div className="mx-auto max-w-4xl">
          <div className="grid grid-cols-1 items-center gap-8 md:grid-cols-2">
            <Skeleton className="aspect-square w-full rounded-xl" />
            <div className="space-y-3">
              <Skeleton className="h-8 w-2/3" />
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-24 w-full" />
            </div>
          </div>
        </div>
      </PageContainer>
    );
  }

  if (error || !product) {
    return (
      <PageContainer>
        <ErrorState message={error ?? "Product not found"} onRetry={load} />
      </PageContainer>
    );
  }

  const isMutating = mutatingItemId === product.id;
  const quantity = Math.min(getSelectedQuantity(product.id), product.stock_quantity) || 1;

  const handleAdd = async () => {
    const ok = await addItem(product.id, quantity);
    if (ok) navigate("/cart");
  };

  return (
    <PageContainer>
      <Link to="/" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-800">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to marketplace
      </Link>
      <div className="mx-auto max-w-4xl">
        <div className="grid grid-cols-1 items-center gap-8 md:grid-cols-2">
          <ProductImage src={product.image_url} alt={product.name} className="mx-auto aspect-square w-full max-w-[240px] rounded-xl sm:max-w-none" />
          <div>
            <div className="mb-2 flex items-start justify-between gap-3">
              <h1 className="text-2xl font-bold text-zinc-900">{product.name}</h1>
              <StockBadge stock={product.stock_quantity} isAvailable={product.is_available} />
            </div>
            <p className="mb-4 text-3xl font-bold text-brand-700">{formatBeans(product.price)}</p>
            <p className="mb-6 whitespace-pre-line text-zinc-600">{product.description || "No description provided."}</p>

            {product.is_available ? (
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                <QuantitySelector
                  quantity={quantity}
                  max={product.stock_quantity}
                  onChange={(q) => setSelectedQuantity(product.id, q)}
                  disabled={isMutating}
                />
                <Button onClick={handleAdd} isLoading={isMutating} className="sm:flex-1">
                  Add to cart — {formatBeans(product.price * quantity)}
                </Button>
              </div>
            ) : (
              <Button disabled fullWidth>
                Currently unavailable
              </Button>
            )}
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
