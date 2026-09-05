import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteProduct, listProducts } from "@/api/products";
import type { Product } from "@/types";
import { DataTable, type Column } from "@/components/admin/DataTable";
import { ProductImage } from "@/components/product/ProductImage";
import { StockBadge } from "@/components/product/StockBadge";
import { FreeBadge } from "@/components/product/FreeBadge";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { useToast } from "@/context/ToastContext";
import { formatIQD } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

export function ProductManagementPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Product | null>(null);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const load = () => {
    setIsLoading(true);
    setError(null);
    listProducts()
      .then(setProducts)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load products"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const handleDelete = async () => {
    if (!pendingDelete) return;
    try {
      await deleteProduct(pendingDelete.id);
      setProducts((prev) => prev.filter((p) => p.id !== pendingDelete.id));
      showToast("Product deleted", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not delete product", "error");
    } finally {
      setPendingDelete(null);
    }
  };

  const filtered = products.filter((p) => p.name.toLowerCase().includes(search.trim().toLowerCase()));

  const columns: Column<Product>[] = [
    {
      key: "product",
      header: "Product",
      render: (p) => (
        <div className="flex items-center gap-3">
          <ProductImage src={p.image_url} alt={p.name} className="h-12 w-12 shrink-0 rounded-lg" />
          <span className="line-clamp-1 font-medium text-zinc-900">{p.name}</span>
        </div>
      ),
    },
    { key: "price", header: "Price", render: (p) => (p.is_free ? <FreeBadge /> : formatIQD(p.price)) },
    { key: "stock", header: "Stock", render: (p) => <span className="tabular-nums">{p.stock_quantity}</span> },
    { key: "availability", header: "Availability", render: (p) => <StockBadge stock={p.stock_quantity} isAvailable={p.is_available} /> },
    { key: "status", header: "Listed", render: (p) => <Badge color={p.is_active ? "green" : "zinc"}>{p.is_active ? "Active" : "Hidden"}</Badge> },
    {
      key: "actions",
      header: "",
      className: "text-right",
      render: (p) => (
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" className="px-2.5 py-1.5 text-xs" onClick={() => navigate(`/admin/products/${p.id}/edit`)}>
            Edit
          </Button>
          <Button variant="ghost" className="px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50" onClick={() => setPendingDelete(p)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search products..." className="input max-w-xs" />
        <Button onClick={() => navigate("/admin/products/new")}>+ Add product</Button>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <DataTable columns={columns} rows={filtered} rowKey={(p) => p.id} isLoading={isLoading} emptyTitle="No products yet" emptyDescription="Add your first product to get started." />
      )}

      <ConfirmDialog
        isOpen={!!pendingDelete}
        title="Delete product"
        message={`Are you sure you want to delete "${pendingDelete?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
