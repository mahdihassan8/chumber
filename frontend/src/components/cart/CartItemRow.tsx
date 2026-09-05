import { Link } from "react-router-dom";
import type { CartItem } from "@/types";
import { ProductImage } from "@/components/product/ProductImage";
import { QuantitySelector } from "@/components/product/QuantitySelector";
import { BeansAmount } from "@/components/common/BeansAmount";
import { useCart } from "@/context/CartContext";

export function CartItemRow({ item }: { item: CartItem }) {
  const { updateItem, removeItem, mutatingItemId } = useCart();
  const isMutating = mutatingItemId === item.id;

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-3 py-4">
      <Link to={`/products/${item.product.id}`} className="shrink-0">
        <ProductImage src={item.product.image_url} alt={item.product.name} className="h-14 w-14 shrink-0 rounded-lg sm:h-16 sm:w-16" />
      </Link>
      <div className="min-w-0 flex-1">
        <Link to={`/products/${item.product.id}`} className="line-clamp-1 font-medium text-zinc-900 hover:text-brand-700">
          {item.product.name}
        </Link>
        <p className="text-sm text-zinc-500">
          <BeansAmount amount={item.product.price} /> each
        </p>
      </div>
      {/* On mobile this row has too many fixed-width controls to share a line
          with the image + name — w-full forces it onto its own line instead
          of overlapping. From sm: up it's back to a single row, unchanged. */}
      <div className="flex w-full items-center justify-between gap-4 sm:w-auto sm:justify-normal">
        <QuantitySelector quantity={item.quantity} max={item.product.stock_quantity} onChange={(q) => updateItem(item.id, q)} disabled={isMutating} size="sm" />
        <div className="text-right font-semibold text-zinc-900 sm:w-20">
          <BeansAmount amount={item.subtotal} />
        </div>
        <button
          onClick={() => removeItem(item.id)}
          disabled={isMutating}
          aria-label={`Remove ${item.product.name}`}
          className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
        >
          <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
          </svg>
        </button>
      </div>
    </div>
  );
}
