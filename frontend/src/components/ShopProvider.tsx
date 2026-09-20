import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";
import type { CartItem, Product } from "@/lib/shop";

interface ShopContextValue {
  cart: CartItem[];
  wishlistIds: string[];
  drawerOpen: boolean;
  addToCart: (product: Product, size?: string, color?: string) => void;
  updateQuantity: (key: string, quantity: number) => void;
  removeFromCart: (key: string) => void;
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
  const [cart, setCart] = useState<CartItem[]>(() => readStored("safyra-cart", []));
  const [wishlistIds, setWishlistIds] = useState<string[]>(() => readStored("safyra-wishlist", []));
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => window.localStorage.setItem("safyra-cart", JSON.stringify(cart)), [cart]);
  useEffect(() => window.localStorage.setItem("safyra-wishlist", JSON.stringify(wishlistIds)), [wishlistIds]);

  const value = useMemo<ShopContextValue>(() => {
    const addToCart = (product: Product, size = product.sizes[0] ?? "Custom", color = product.colors[0] ?? "As shown") => {
      const key = `${product.id}-${size}-${color}`;
      setCart((current) => {
        const existing = current.find((item) => item.key === key);
        if (existing) return current.map((item) => (item.key === key ? { ...item, quantity: item.quantity + 1 } : item));
        return [...current, { key, productId: product.id, title: product.title, imageUrl: product.image_url, price: product.price, size, color, quantity: 1 }];
      });
      setDrawerOpen(true);
      toast.success("Added to your bag", { description: product.title });
    };
    const updateQuantity = (key: string, quantity: number) => {
      if (quantity < 1) setCart((current) => current.filter((item) => item.key !== key));
      else setCart((current) => current.map((item) => (item.key === key ? { ...item, quantity } : item)));
    };
    const removeFromCart = (key: string) => setCart((current) => current.filter((item) => item.key !== key));
    const toggleWishlist = (productId: string) => {
      setWishlistIds((current) => current.includes(productId) ? current.filter((id) => id !== productId) : [...current, productId]);
      toast(wishlistIds.includes(productId) ? "Removed from wishlist" : "Saved to wishlist");
    };
    return {
      cart,
      wishlistIds,
      drawerOpen,
      addToCart,
      updateQuantity,
      removeFromCart,
      toggleWishlist,
      openDrawer: () => setDrawerOpen(true),
      closeDrawer: () => setDrawerOpen(false),
      cartCount: cart.reduce((sum, item) => sum + item.quantity, 0),
      cartTotal: cart.reduce((sum, item) => sum + item.price * item.quantity, 0),
    };
  }, [cart, wishlistIds, drawerOpen]);

  return <ShopContext.Provider value={value}>{children}</ShopContext.Provider>;
}

export function useShop() {
  const value = useContext(ShopContext);
  if (!value) throw new Error("useShop must be used within ShopProvider");
  return value;
}