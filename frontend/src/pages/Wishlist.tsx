import { Link } from "react-router-dom";
import { Heart } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import BrandHeader from "@/components/BrandHeader";
import ProductCard from "@/components/ProductCard";
import { useShop } from "@/components/ShopProvider";
import { apiGet } from "@/lib/api";
import type { Product } from "@/lib/shop";

export default function Wishlist() {
  const { wishlistIds } = useShop();
  const { data: products = [] } = useQuery({ queryKey: ["products", "wishlist"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const saved = products.filter((product) => wishlistIds.includes(product.id));
  return <div className="page-shell"><BrandHeader /><main className="simple-page"><div className="simple-heading wishlist-heading"><div><span className="eyebrow">Saved for later</span><h1>Your wishlist</h1><p>Keep the pieces that stay with you.</p></div><Link to="/shop" className="underlined-link" data-testid="wishlist-continue-shopping">Continue shopping</Link></div>{saved.length === 0 ? <div className="empty-state large-empty"><Heart size={28} /><h2>Nothing saved yet.</h2><p>Tap the heart on a piece you love and find it here.</p><Link to="/shop" className="button button-dark" data-testid="wishlist-empty-shop-link">Explore the edit</Link></div> : <div className="product-grid">{saved.map((product, index) => <ProductCard key={product.id} product={product} index={index} />)}</div>}</main></div>;
}