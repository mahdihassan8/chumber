import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { checkout } from "@/api/orders";
import { PageContainer } from "@/components/layout/PageContainer";
import { CartSummary } from "@/components/cart/CartSummary";
import { ProductImage } from "@/components/product/ProductImage";
import { Button } from "@/components/common/Button";
import { BeansAmount } from "@/components/common/BeansAmount";
import { ApiRequestError } from "@/api/client";

export function CheckoutPage() {
  const { cart, clearLocal, refresh } = useCart();
  const { setUser, user } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!cart || cart.items.length === 0) {
    return <Navigate to="/cart" replace />;
  }

  const insufficient = cart.balance < cart.total;

  const handlePlaceOrder = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await checkout();
      clearLocal();
      if (user) setUser({ ...user, balance: response.new_balance });
      showToast("Order placed successfully!", "success");
      navigate("/history", { state: { justOrderedId: response.order.id } });
    } catch (err) {
      const message = err instanceof ApiRequestError ? err.message : "Checkout failed. Please try again.";
      setError(message);
      showToast(message, "error");
      await refresh();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageContainer className="max-w-4xl">
      <h1 className="mb-6 text-2xl font-bold text-zinc-900">Checkout</h1>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="card divide-y divide-zinc-100 px-5 lg:col-span-2">
          {cart.items.map((item) => (
            <div key={item.id} className="flex items-center gap-4 py-4">
              <ProductImage src={item.product.image_url} alt={item.product.name} className="h-14 w-14 shrink-0 rounded-lg sm:h-16 sm:w-16" />
              <div className="min-w-0 flex-1">
                <p className="line-clamp-1 font-medium text-zinc-900">{item.product.name}</p>
                <p className="text-sm text-zinc-500">Qty {item.quantity}</p>
              </div>
              <span className="font-semibold text-zinc-900">
                <BeansAmount amount={item.subtotal} />
              </span>
            </div>
          ))}
        </div>
        <div>
          <CartSummary total={cart.total} balance={cart.balance}>
            {error && (
              <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
                {error}
              </p>
            )}
            <Button fullWidth onClick={handlePlaceOrder} isLoading={isSubmitting} disabled={insufficient}>
              {isSubmitting ? "Placing order..." : "Place order"}
            </Button>
          </CartSummary>
        </div>
      </div>
    </PageContainer>
  );
}
