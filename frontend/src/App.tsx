import { Routes, Route } from "react-router-dom";
import { Navigate } from "react-router-dom";
import Home from "@/pages/Home";
import Shop from "@/pages/Shop";
import Product from "@/pages/Product";
import Cart from "@/pages/Cart";
import Wishlist from "@/pages/Wishlist";
import Admin from "@/pages/Admin";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import Account from "@/pages/Account";
import AdminLogin from "@/pages/AdminLogin";
import Checkout from "@/pages/Checkout";
import Information from "@/pages/Information";
import { ShopProvider } from "@/components/ShopProvider";
import CartDrawer from "@/components/CartDrawer";
import { AuthProvider, useAuth } from "@/components/AuthProvider";
import { useLocation } from "react-router-dom";
import { useEffect, type ReactNode } from "react";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo({ top: 0, left: 0 }); }, [pathname]);
  return null;
}

function CustomerRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <div className="route-loading" data-testid="customer-route-loading">Verifying your account…</div>;
  if (!user || user.role !== "customer") return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

function AdminRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="route-loading" data-testid="admin-route-loading">Verifying secure access…</div>;
  if (!user || user.role !== "admin") return <Navigate to="/admin-login" replace />;
  return children;
}

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <AuthProvider>
      <ShopProvider>
        <ScrollToTop />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/shop" element={<Shop />} />
          <Route path="/product/:productId" element={<Product />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/information" element={<Information />} />
          <Route path="/wishlist" element={<Wishlist />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/account" element={<CustomerRoute><Account /></CustomerRoute>} />
          <Route path="/admin-login" element={<AdminLogin />} />
          <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <CartDrawer />
      </ShopProvider>
    </AuthProvider>
  );
}
