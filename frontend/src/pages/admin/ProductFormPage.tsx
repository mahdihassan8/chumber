import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProduct } from "@/api/products";
import type { Product } from "@/types";
import { ProductForm } from "@/components/admin/ProductForm";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";

export function ProductFormPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [product, setProduct] = useState<Product | null>(null);
  const [isLoading, setIsLoading] = useState(isEdit);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setIsLoading(true);
    getProduct(id)
      .then(setProduct)
      .catch(() => setError("Could not load product"))
      .finally(() => setIsLoading(false));
  }, [id]);

  return (
    <div>
      <Link to="/admin/products" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-800">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to products
      </Link>
      <h1 className="mb-6 text-xl font-bold text-zinc-900">{isEdit ? "Edit Product" : "Add Product"}</h1>

      {isLoading ? <Skeleton className="h-96 max-w-xl" /> : error ? <ErrorState message={error} /> : <ProductForm existingProduct={product ?? undefined} />}
    </div>
  );
}
