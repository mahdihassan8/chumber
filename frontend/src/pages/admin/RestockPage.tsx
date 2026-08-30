import { useEffect, useState } from "react";
import { listProducts, restockProduct } from "@/api/products";
import type { Product } from "@/types";
import { ProductImage } from "@/components/product/ProductImage";
import { StockBadge } from "@/components/product/StockBadge";
import { Button } from "@/components/common/Button";
import { ErrorState, EmptyState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";
import { useToast } from "@/context/ToastContext";
import { ApiRequestError } from "@/api/client";

function RestockRow({ product, onRestocked }: { product: Product; onRestocked: (p: Product) => void }) {
  const [quantity, setQuantity] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { showToast } = useToast();

  const handleRestock = async () => {
    const value = Number(quantity);
    if (!Number.isInteger(value) || value <= 0) {
      showToast("Enter a whole number greater than 0", "error");
      return;
    }
    setIsSubmitting(true);
    try {
      const updated = await restockProduct(product.id, value);
      onRestocked(updated);
      showToast(`${product.name} restocked (+${value})`, "success");
      setQuantity("");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not restock product", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-4 py-4">
      <ProductImage src={product.image_url} alt={product.name} className="h-12 w-12 shrink-0 rounded-lg" />
      <div className="min-w-[10rem] flex-1">
        <p className="font-medium text-zinc-900">{product.name}</p>
        <div className="mt-1">
          <StockBadge stock={product.stock_quantity} isAvailable={product.is_available} />
        </div>
      </div>
      <input
        type="number"
        min="1"
        step="1"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        placeholder="Qty"
        className="input w-24"
        onKeyDown={(e) => e.key === "Enter" && handleRestock()}
      />
      <Button onClick={handleRestock} isLoading={isSubmitting} disabled={!quantity}>
        Restock
      </Button>
    </div>
  );
}

export function RestockPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setIsLoading(true);
    setError(null);
    listProducts()
      .then((data) => setProducts(data.sort((a, b) => a.stock_quantity - b.stock_quantity)))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load products"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const handleRestocked = (updated: Product) => {
    setProducts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)).sort((a, b) => a.stock_quantity - b.stock_quantity));
  };

  return (
    <div>
      <p className="mb-5 text-sm text-zinc-500">Products are sorted by lowest stock first. Enter a quantity to add to existing stock.</p>
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : products.length === 0 ? (
        <EmptyState title="No products yet" />
      ) : (
        <div className="card divide-y divide-zinc-100 px-5">
          {products.map((p) => (
            <RestockRow key={p.id} product={p} onRestocked={handleRestocked} />
          ))}
        </div>
      )}
    </div>
  );
}
