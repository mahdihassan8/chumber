import { useEffect, useMemo, useState } from "react";
import { listProducts } from "@/api/products";
import type { Product } from "@/types";
import { PageContainer } from "@/components/layout/PageContainer";
import { ProductList } from "@/components/product/ProductList";
import { ErrorState } from "@/components/common/ErrorState";
import { ApiRequestError } from "@/api/client";

export function MarketplacePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const load = () => {
    setIsLoading(true);
    setError(null);
    listProducts()
      .then(setProducts)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load products"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return products;
    const q = search.trim().toLowerCase();
    return products.filter((p) => p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q));
  }, [products, search]);

  return (
    <PageContainer>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Marketplace</h1>
          <p className="text-sm text-zinc-500">Browse available products</p>
        </div>
        <div className="relative w-full sm:w-72">
          <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search products..."
            className="input pl-9"
            aria-label="Search products"
          />
        </div>
      </div>

      {error ? <ErrorState message={error} onRetry={load} /> : <ProductList products={filtered} isLoading={isLoading} />}
    </PageContainer>
  );
}
