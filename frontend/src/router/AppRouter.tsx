import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { ProtectedRoute, AdminRoute } from "@/components/layout/ProtectedRoute";
import { LoginPage } from "@/pages/LoginPage";
import { MarketplacePage } from "@/pages/MarketplacePage";
import { ProductDetailsPage } from "@/pages/ProductDetailsPage";
import { CartPage } from "@/pages/CartPage";
import { CheckoutPage } from "@/pages/CheckoutPage";
import { PurchaseHistoryPage } from "@/pages/PurchaseHistoryPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { GiveawayPage } from "@/pages/GiveawayPage";

import { AdminLayout } from "@/pages/admin/AdminLayout";
import { OverviewPage } from "@/pages/admin/OverviewPage";
import { UserManagementPage } from "@/pages/admin/UserManagementPage";
import { UserFormPage } from "@/pages/admin/UserFormPage";
import { UserDetailsPage } from "@/pages/admin/UserDetailsPage";
import { ProductManagementPage } from "@/pages/admin/ProductManagementPage";
import { ProductFormPage } from "@/pages/admin/ProductFormPage";
import { RestockPage } from "@/pages/admin/RestockPage";
import { BalanceManagementPage } from "@/pages/admin/BalanceManagementPage";
import { OrderManagementPage } from "@/pages/admin/OrderManagementPage";
import { AIRestockingPage } from "@/pages/admin/AIRestockingPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<MarketplacePage />} />
          <Route path="/products/:id" element={<ProductDetailsPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/history" element={<PurchaseHistoryPage />} />
          <Route path="/giveaway" element={<GiveawayPage />} />
          <Route path="/profile" element={<ProfilePage />} />

          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<OverviewPage />} />
              <Route path="users" element={<UserManagementPage />} />
              <Route path="users/new" element={<UserFormPage />} />
              <Route path="users/:id" element={<UserDetailsPage />} />
              <Route path="users/:id/edit" element={<UserFormPage />} />
              <Route path="products" element={<ProductManagementPage />} />
              <Route path="products/new" element={<ProductFormPage />} />
              <Route path="products/:id/edit" element={<ProductFormPage />} />
              <Route path="restock" element={<RestockPage />} />
              <Route path="balance" element={<BalanceManagementPage />} />
              <Route path="orders" element={<OrderManagementPage />} />
              <Route path="ai-restocking" element={<AIRestockingPage />} />
            </Route>
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
