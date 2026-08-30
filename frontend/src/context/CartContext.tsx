import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import * as cartApi from "@/api/cart";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import type { Cart } from "@/types";
import { ApiRequestError } from "@/api/client";

interface CartContextValue {
  cart: Cart | null;
  isLoading: boolean;
  mutatingItemId: string | null;
  itemCount: number;
  refresh: () => Promise<void>;
  addItem: (productId: string, quantity?: number) => Promise<boolean>;
  updateItem: (itemId: string, quantity: number) => Promise<void>;
  removeItem: (itemId: string) => Promise<void>;
  clearLocal: () => void;
  /** The quantity a user has picked on a product card/details page but not
   * yet added to the cart. Lives here (not component-local state) so it
   * survives navigating away and back — the product page components mount
   * fresh every visit, but CartProvider wraps the whole app and doesn't. */
  getSelectedQuantity: (productId: string) => number;
  setSelectedQuantity: (productId: string, quantity: number) => void;
}

const CartContext = createContext<CartContextValue | undefined>(undefined);

export function CartProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [mutatingItemId, setMutatingItemId] = useState<string | null>(null);
  const [selectedQuantities, setSelectedQuantities] = useState<Record<string, number>>({});

  const refresh = useCallback(async () => {
    if (!user) {
      setCart(null);
      setSelectedQuantities({});
      return;
    }
    setIsLoading(true);
    try {
      const data = await cartApi.getCart();
      setCart(data);
    } catch {
      // Non-fatal: cart widgets fall back to empty state.
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const addItem = useCallback(
    async (productId: string, quantity = 1) => {
      setMutatingItemId(productId);
      try {
        const data = await cartApi.addToCart(productId, quantity);
        setCart(data);
        showToast("Added to cart", "success");
        // Reset the pending picker back to 1 now that it's actually in the cart.
        setSelectedQuantities((prev) => {
          const next = { ...prev };
          delete next[productId];
          return next;
        });
        return true;
      } catch (err) {
        const message = err instanceof ApiRequestError ? err.message : "Could not add to cart";
        showToast(message, "error");
        return false;
      } finally {
        setMutatingItemId(null);
      }
    },
    [showToast]
  );

  const getSelectedQuantity = useCallback((productId: string) => selectedQuantities[productId] ?? 1, [selectedQuantities]);

  const setSelectedQuantity = useCallback((productId: string, quantity: number) => {
    setSelectedQuantities((prev) => ({ ...prev, [productId]: quantity }));
  }, []);

  const updateItem = useCallback(
    async (itemId: string, quantity: number) => {
      const previous = cart;
      setMutatingItemId(itemId);
      try {
        const data = await cartApi.updateCartItem(itemId, quantity);
        setCart(data);
      } catch (err) {
        setCart(previous);
        const message = err instanceof ApiRequestError ? err.message : "Could not update quantity";
        showToast(message, "error");
      } finally {
        setMutatingItemId(null);
      }
    },
    [cart, showToast]
  );

  const removeItem = useCallback(
    async (itemId: string) => {
      setMutatingItemId(itemId);
      try {
        const data = await cartApi.removeCartItem(itemId);
        setCart(data);
      } catch (err) {
        const message = err instanceof ApiRequestError ? err.message : "Could not remove item";
        showToast(message, "error");
      } finally {
        setMutatingItemId(null);
      }
    },
    [showToast]
  );

  const clearLocal = useCallback(() => {
    setCart((prev) => (prev ? { ...prev, items: [], total: 0 } : prev));
  }, []);

  const itemCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;

  return (
    <CartContext.Provider
      value={{
        cart,
        isLoading,
        mutatingItemId,
        itemCount,
        refresh,
        addItem,
        updateItem,
        removeItem,
        clearLocal,
        getSelectedQuantity,
        setSelectedQuantity,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
