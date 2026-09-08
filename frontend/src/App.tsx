import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { BalanceProvider } from "@/context/BalanceContext";
import { CartProvider } from "@/context/CartContext";
import { RegionProvider } from "@/context/RegionContext";
import { ToastProvider } from "@/context/ToastContext";
import { ToastContainer } from "@/components/common/ToastContainer";
import { AppRouter } from "@/router/AppRouter";

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <RegionProvider>
          <BalanceProvider>
          <CartProvider>
            <AppRouter />
            <ToastContainer />
          </CartProvider>
          </BalanceProvider>
          </RegionProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
