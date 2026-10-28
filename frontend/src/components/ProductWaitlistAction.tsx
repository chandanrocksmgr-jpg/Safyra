import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { BellRing } from "lucide-react";
import { useLocation } from "react-router-dom";
import WaitlistModal from "@/components/WaitlistModal";
import { apiGet } from "@/lib/api";
import { hasVariants, isProductUnavailable, type Product } from "@/lib/shop";

export default function ProductWaitlistAction() {
  const { pathname } = useLocation();
  const productId = pathname.startsWith("/product/") ? decodeURIComponent(pathname.slice("/product/".length)) : "";
  const [target, setTarget] = useState<Element | null>(null);
  const [open, setOpen] = useState(false);
  const { data: product } = useQuery({ queryKey: ["product", productId], queryFn: () => apiGet<Product>(`/products/${productId}`), enabled: Boolean(productId), retry: false });

  useEffect(() => {
    if (!productId) { setTarget(null); setOpen(false); return; }
    const findTarget = () => setTarget(document.querySelector(".product-detail-copy .product-actions"));
    findTarget();
    const observer = new MutationObserver(findTarget);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [productId]);

  // Variant products handle "Notify me" per colour and size on the product page itself.
  if (!product || !isProductUnavailable(product) || (hasVariants(product) && product.availability !== "Currently unavailable")) return null;
  return <>
    {target && createPortal(<button className="button button-dark button-large waitlist-product-trigger" onClick={() => setOpen(true)} data-testid="join-waitlist-button"><BellRing size={17} /> Limited availability · Join the waitlist</button>, target)}
    {open && createPortal(<WaitlistModal product={product} onClose={() => setOpen(false)} />, document.body)}
  </>;
}