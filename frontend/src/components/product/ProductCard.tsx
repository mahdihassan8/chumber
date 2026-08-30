import { Link } from "react-router-dom";
import type { Product } from "@/types";
import { ProductImage } from "@/components/product/ProductImage";
import { StockBadge } from "@/components/product/StockBadge";
import { QuantitySelector } from "@/components/product/QuantitySelector";
import { Button } from "@/components/common/Button";
import { useCart } from "@/context/CartContext";
import { formatBeans } from "@/utils/assets";

export function ProductCard({ product }: { product: Product }) {
  const { addItem, mutatingItemId, getSelectedQuantity, setSelectedQuantity } = useCart();
  // Clamp in case stock dropped since this quantity was picked (e.g. bought
  // by someone else while this tab sat on a different page) — the picker is
  // remembered across navigation, but it must never offer more than what's
  // actually in stock right now.
  const quantity = Math.min(getSelectedQuantity(product.id), product.stock_quantity) || 1;
  const isMutating = mutatingItemId === product.id;

  const handleAdd = async () => {
    await addItem(product.id, quantity);
  };

  return (
    <div className="card group flex flex-col overflow-hidden transition-shadow hover:shadow-card-hover">
      <Link to={`/products/${product.id}`} className="relative block">
        <ProductImage
          src={product.image_url}
          alt={product.name}
          className="h-28 w-full transition-transform duration-300 group-hover:scale-[1.03] sm:h-40"
        />
      </Link>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <Link to={`/products/${product.id}`} className="line-clamp-1 font-semibold text-zinc-900 hover:text-brand-700">
            {product.name}
          </Link>
        </div>
        <p className="line-clamp-2 flex-1 text-sm text-zinc-500">{product.description}</p>
        <div className="flex items-center justify-between pt-1">
          <span className="text-lg font-bold text-zinc-900">{formatBeans(product.price)}</span>
          <StockBadge stock={product.stock_quantity} isAvailable={product.is_available} />
        </div>
        {product.is_available ? (
          <div className="mt-2 flex items-center gap-2">
            <QuantitySelector
              quantity={quantity}
              max={product.stock_quantity}
              onChange={(q) => setSelectedQuantity(product.id, q)}
              disabled={isMutating}
              size="sm"
            />
            <Button onClick={handleAdd} isLoading={isMutating} className="flex-1">
              Add
            </Button>
          </div>
        ) : (
          <Button disabled className="mt-2 w-full">
            Unavailable
          </Button>
        )}
      </div>
    </div>
  );
}
