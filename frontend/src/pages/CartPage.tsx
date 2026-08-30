import { Link, useNavigate } from "react-router-dom";
import { useCart } from "@/context/CartContext";
import { PageContainer } from "@/components/layout/PageContainer";
import { CartItemRow } from "@/components/cart/CartItemRow";
import { CartSummary } from "@/components/cart/CartSummary";
import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";

export function CartPage() {
  const { cart, isLoading } = useCart();
  const navigate = useNavigate();

  return (
    <PageContainer>
      <h1 className="mb-6 text-2xl font-bold text-zinc-900">Shopping Cart</h1>

      {isLoading && !cart ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : !cart || cart.items.length === 0 ? (
        <EmptyState
          title="Your cart is empty"
          description="Browse the marketplace and add products to get started."
          action={<Button onClick={() => navigate("/")}>Browse products</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="card divide-y divide-zinc-100 px-5 lg:col-span-2">
            {cart.items.map((item) => (
              <CartItemRow key={item.id} item={item} />
            ))}
          </div>
          <div>
            <CartSummary total={cart.total} balance={cart.balance}>
              <Button fullWidth onClick={() => navigate("/checkout")}>
                Proceed to checkout
              </Button>
              <Link to="/" className="block text-center text-sm font-medium text-zinc-500 hover:text-zinc-800">
                Continue shopping
              </Link>
            </CartSummary>
          </div>
        </div>
      )}
    </PageContainer>
  );
}
