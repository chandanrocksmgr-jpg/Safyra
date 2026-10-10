import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import type { CartItem, Product } from "@/lib/shop";
import type { AccountResponse } from "@/lib/auth";
import { apiGet, apiPut } from "@/lib/api";
import { availableQuantity } from "@/lib/shop";
import { useAuth } from "@/components/AuthProvider";

interface ShopContextValue {
  cart: CartItem[];
  orderNote: string;
  setOrderNote: (note: string) => void;
  wishlistIds: string[];
  drawerOpen: boolean;
  addToCart: (product: Product, size?: string, color?: string) => void;
  updateQuantity: (key: string, quantity: number) => void;
  removeFromCart: (key: string) => void;
  clearCart: () => void;
  toggleWishlist: (productId: string) => void;
  openDrawer: () => void;
  closeDrawer: () => void;
  cartCount: number;
  cartTotal: number;
}

const readStored = <T,>(key: string, fallback: T): T => {
  if (typeof window === "undefined") return fallback;
  try {
    const value = window.localStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
  }
};

const ShopContext = createContext<ShopContextValue | null>(null);

export function ShopProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [cart, setCart] = useState<CartItem[]>(() => readStored("safyra-cart", []));
  const [orderNote, setOrderNote] = useState(() => readStored("safyra-order-note", ""));
  const [wishlistIds, setWishlistIds] = useState<string[]>(() => readStored("safyra-wishlist", []));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const previousUserId = useRef<string | null>(null);
  const { data: account } = useQuery({
    queryKey: ["account", user?.id],
    queryFn: () => apiGet<AccountResponse>("/account"),
    enabled: Boolean(user),
    retry: false,
  });
  const { data: products = [] } = useQuery({ queryKey: ["products", "cart-availability"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const saveState = useMutation({ mutationFn: (state: { wishlist_ids: string[]; cart: CartItem[] }) => apiPut<void>("/account/state", state) });

  useEffect(() => { window.localStorage.setItem("safyra-cart", JSON.stringify(cart)); }, [cart]);
  useEffect(() => { window.localStorage.setItem("safyra-order-note", JSON.stringify(orderNote)); }, [orderNote]);
  useEffect(() => { window.localStorage.setItem("safyra-wishlist", JSON.stringify(wishlistIds)); }, [wishlistIds]);
  useEffect(() => {
    if (account && user) {
      setCart(account.cart);
      setWishlistIds(account.wishlist_ids);
      previousUserId.current = user.id;
    } else if (!user && previousUserId.current) {
      setCart([]);
      setWishlistIds([]);
      previousUserId.current = null;
    }
  }, [account, user]);

  const value = useMemo<ShopContextValue>(() => {
    const addToCart = (product: Product, size = product.sizes[0] ?? "Custom", color = product.colors[0] ?? "As shown") => {
      const limit = availableQuantity(product, size);
      if (limit < 1) { toast.error("This selection is currently unavailable"); return; }
      const key = `${product.id}-${size}-${color}`;
      setCart((current) => {
        const existing = current.find((item) => item.key === key);
        if (existing && existing.quantity >= limit) { toast.error(`Only ${limit} available in this size`); return current; }
        const next = existing ? current.map((item) => (item.key === key ? { ...item, quantity: item.quantity + 1 } : item)) : [...current, { key, productId: product.id, slug: product.slug, title: product.title, imageUrl: product.image_url, price: product.price, size, color, quantity: 1 }];
        if (user) saveState.mutate({ cart: next, wishlist_ids: wishlistIds });
        return next;
      });
      setDrawerOpen(true);
      toast.success("Added to your bag", { description: product.title });
    };
    const updateQuantity = (key: string, quantity: number) => {
      setCart((current) => {
        const item = current.find((entry) => entry.key === key);
        const product = item ? products.find((entry) => entry.id === item.productId) : undefined;
        const limit = item && product ? availableQuantity(product, item.size) : Number.POSITIVE_INFINITY;
        if (quantity > limit) { toast.error(limit > 0 ? `Only ${limit} available in this size` : "This selection is currently unavailable"); return current; }
        const next = quantity < 1 ? current.filter((item) => item.key !== key) : current.map((item) => (item.key === key ? { ...item, quantity } : item));
        if (user) saveState.mutate({ cart: next, wishlist_ids: wishlistIds });
        return next;
      });
    };
    const removeFromCart = (key: string) => setCart((current) => {
      const next = current.filter((item) => item.key !== key);
      if (user) saveState.mutate({ cart: next, wishlist_ids: wishlistIds });
      return next;
    });
    const clearCart = () => {
      setCart([]);
      setOrderNote("");
      if (user) saveState.mutate({ cart: [], wishlist_ids: wishlistIds });
    };
    const toggleWishlist = (productId: string) => {
      setWishlistIds((current) => {
        const next = current.includes(productId) ? current.filter((id) => id !== productId) : [...current, productId];
        if (user) saveState.mutate({ cart, wishlist_ids: next });
        return next;
      });
      toast(wishlistIds.includes(productId) ? "Removed from wishlist" : "Saved to wishlist");
    };
    return {
      cart,
      orderNote,
      setOrderNote,
      wishlistIds,
      drawerOpen,
      addToCart,
      updateQuantity,
      removeFromCart,
      clearCart,
      toggleWishlist,
      openDrawer: () => setDrawerOpen(true),
      closeDrawer: () => setDrawerOpen(false),
      cartCount: cart.reduce((sum, item) => sum + item.quantity, 0),
      cartTotal: cart.reduce((sum, item) => sum + item.price * item.quantity, 0),
    };
  }, [cart, orderNote, wishlistIds, drawerOpen, user, saveState, products]);

  return <ShopContext.Provider value={value}>{children}</ShopContext.Provider>;
}

export function useShop() {
  const value = useContext(ShopContext);
  if (!value) throw new Error("useShop must be used within ShopProvider");
  return value;
}