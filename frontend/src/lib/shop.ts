export interface Product {
  id: string;
  title: string;
  slug: string;
  category: string;
  collection: string;
  fabric: string;
  craft: string;
  price: number;
  mrp: number | null;
  stock: number;
  stock_by_size: Record<string, number>;
  sizes: string[];
  colors: string[];
  image_url: string;
  image_urls: string[];
  description: string;
  fit: string;
  measurements: string;
  transparency: string;
  lining: string;
  care: string;
  dispatch_days: string;
  availability: string;
  customisation: string;
  origin: string;
  occasion: string[];
  style_keywords: string[];
  size_guide_image: string;
  complete_look_ids: string[];
  tags: string[];
  featured: boolean;
  best_seller: boolean;
  new_arrival: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductFacets {
  categories: string[];
  collections: string[];
  sizes: string[];
  colors: string[];
  fabrics: string[];
  crafts: string[];
  availabilities: string[];
  price_min: number;
  price_max: number;
  has_best_sellers: boolean;
}

export interface CartItem {
  key: string;
  productId: string;
  slug?: string;
  title: string;
  imageUrl: string;
  price: number;
  size: string;
  color: string;
  quantity: number;
}

export const formatPrice = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);

export const whatsappUrl = (message: string) =>
  `https://wa.me/918090164929?text=${encodeURIComponent(message)}`;

export const productWhatsappUrl = (product: Product) =>
  whatsappUrl(
    `Hello SAFYRA, I would like help with ${product.title}. Please advise on sizing, customisation and dispatch. Product: https://safyra.co/product/${product.slug}`,
  );

export const cartWhatsappUrl = (items: CartItem[], total: number) =>
  whatsappUrl(
    `Hello SAFYRA, I would like to enquire about ordering: ${items
      .map((item) => `${item.title} (${item.size}, ${item.color}) x${item.quantity}`)
      .join(", ")}. Estimated total: ${formatPrice(total)}.`,
  );
