import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { Product } from "@/types";
import { createProduct, updateProduct, uploadProductImage } from "@/api/products";
import { useToast } from "@/context/ToastContext";
import { TextField } from "@/components/common/TextField";
import { Button } from "@/components/common/Button";
import { ProductImage } from "@/components/product/ProductImage";
import { ApiRequestError } from "@/api/client";

interface ProductFormProps {
  existingProduct?: Product;
}

export function ProductForm({ existingProduct }: ProductFormProps) {
  const isEdit = !!existingProduct;
  const navigate = useNavigate();
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState(existingProduct?.name ?? "");
  const [description, setDescription] = useState(existingProduct?.description ?? "");
  const [price, setPrice] = useState(existingProduct ? String(existingProduct.price) : "");
  const [stock, setStock] = useState(existingProduct ? String(existingProduct.stock_quantity) : "");
  const [imageUrl, setImageUrl] = useState<string | null>(existingProduct?.image_url ?? null);
  const [isActive, setIsActive] = useState(existingProduct?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);

  const handleImageSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !existingProduct) return;
    setIsUploadingImage(true);
    try {
      const updated = await uploadProductImage(existingProduct.id, file);
      setImageUrl(updated.image_url);
      showToast("Image uploaded", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not upload image", "error");
    } finally {
      setIsUploadingImage(false);
      e.target.value = "";
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const priceNum = Number(price);
    const stockNum = Number(stock);
    if (!name.trim()) return setError("Product name is required");
    if (!priceNum || priceNum <= 0) return setError("Price must be greater than 0");
    if (!Number.isInteger(stockNum) || stockNum < 0) return setError("Stock quantity must be a non-negative whole number");

    setIsSubmitting(true);
    try {
      if (isEdit && existingProduct) {
        await updateProduct(existingProduct.id, { name, description, price: priceNum, stock_quantity: stockNum, is_active: isActive });
        showToast("Product updated", "success");
      } else {
        const created = await createProduct({ name, description, price: priceNum, stock_quantity: stockNum, is_active: isActive });
        showToast("Product created", "success");
        navigate(`/admin/products/${created.id}/edit`);
        return;
      }
      navigate("/admin/products");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not save product");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card max-w-xl space-y-4 p-6">
      {isEdit && (
        <div>
          <span className="label">Product image</span>
          <div className="flex items-center gap-4">
            <ProductImage src={imageUrl} alt={name} className="h-20 w-20 rounded-lg" />
            <div>
              <Button type="button" variant="secondary" isLoading={isUploadingImage} onClick={() => fileInputRef.current?.click()}>
                Upload image
              </Button>
              <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleImageSelect} />
            </div>
          </div>
        </div>
      )}

      <TextField label="Product name" name="name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} />

      <div>
        <label htmlFor="description" className="label">
          Description
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="input resize-none"
          placeholder="Describe the product..."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <TextField label="Price (USD)" name="price" type="number" min="0.01" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} required />
        <TextField label="Stock quantity" name="stock_quantity" type="number" min="0" step="1" value={stock} onChange={(e) => setStock(e.target.value)} required />
      </div>

      <label className="flex items-center gap-2.5 text-sm font-medium text-zinc-700">
        <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="h-4 w-4 rounded border-zinc-300 text-brand-600 focus:ring-brand-500" />
        Listed as active
      </label>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
          {error}
        </p>
      )}

      <div className="flex gap-2 pt-2">
        <Button type="submit" isLoading={isSubmitting}>
          {isEdit ? "Save changes" : "Create product"}
        </Button>
        <Button type="button" variant="secondary" onClick={() => navigate("/admin/products")}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
