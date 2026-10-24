/** A colour option: name, approximate swatch and the photos manually assigned to it. Mirrors backend ProductColorOption. */
export interface ProductColorOption {
  name: string;
  swatch: string;
  image_urls: string[];
}

export interface ProductSetType {
  id: string;
  name: string;
  price: number;
  mrp: number | null;
}

/** One sellable row: combination (set type) × colour × size. Mirrors backend ProductVariant. */
export interface ProductVariant {
  id: string;
  set_type_id: string;
  color: string;
  size: string;
  price: number | null;
  mrp: number | null;
  stock: number;
  available: boolean;
}

export interface Product {
  id: string;
  title: string;
  slug: string;
  category: string;
  collection: string;
  fabric: string;
  craft: string;
  hsn_code: string;
  price: number;
  mrp: number | null;
  stock: number;
  stock_by_size: Record<string, number>;
  sizes: string[];
  colors: string[];
  color_options: ProductColorOption[];
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
  status: "draft" | "active" | "archived";
  set_types: ProductSetType[];
  variants: ProductVariant[];
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
  compareAtPrice?: number | null;
  setType?: string;
  setTypeId?: string;
  size: string;
  color: string;
  quantity: number;
}

export const isMadeToOrder = (product: Pick<Product, "availability">) => product.availability.trim().toLowerCase() === "made to order";

type StockInput = Pick<Product, "availability" | "sizes" | "stock" | "stock_by_size"> & Partial<Pick<Product, "variants" | "colors">>;

export const hasVariants = (product: StockInput) => Boolean(product.variants?.length);

export const findVariant = (product: StockInput, setTypeId: string, size: string, color: string) => {
  // Dimensions a product does not use are stored as "" (carts may carry placeholders such as "As shown").
  const wantedSize = product.sizes.length ? size : "";
  const wantedColor = product.colors?.length ? color : "";
  return product.variants?.find((variant) => variant.set_type_id === setTypeId && variant.size === wantedSize && variant.color === wantedColor);
};

export const isVariantSellable = (variant: ProductVariant | undefined) => Boolean(variant && variant.available && variant.stock > 0);

/** Units a customer may add. With a variant table, stock is exact per combination × colour × size for every product. */
export const availableQuantity = (product: StockInput, size: string, color = "", setTypeId = "") => {
  if (product.availability === "Currently unavailable" || !product.sizes.length) return 0;
  if (hasVariants(product)) {
    const variant = findVariant(product, setTypeId, size, color);
    return variant && variant.available ? Math.max(0, variant.stock) : 0;
  }
  if (isMadeToOrder(product)) return Number.POSITIVE_INFINITY;
  if (Object.hasOwn(product.stock_by_size, size)) return Math.max(0, product.stock_by_size[size]);
  return Math.max(0, product.stock);
};

export const isProductUnavailable = (product: StockInput) => {
  if (product.availability === "Currently unavailable" || !product.sizes.length) return true;
  if (hasVariants(product)) return !product.variants?.some(isVariantSellable);
  if (isMadeToOrder(product)) return false;
  return product.sizes.every((size) => availableQuantity(product, size) < 1);
};

export const defaultSetTypeId = (product: Pick<Product, "set_types">) => product.set_types[0]?.id ?? "";

/** Price for a selection: variant override → combination price → product price. */
export const selectionPrice = (product: Product, setTypeId: string, size: string, color: string) => {
  const variant = size ? findVariant(product, setTypeId, size, color) : undefined;
  const setType = product.set_types.find((item) => item.id === setTypeId);
  return { price: variant?.price ?? setType?.price ?? product.price, mrp: variant?.mrp ?? setType?.mrp ?? product.mrp };
};

/** Lowest and highest price across offered variants, for "From ₹…" on product cards. */
export const priceRange = (product: Product) => {
  const offered = product.variants.filter((variant) => variant.available);
  const prices = offered.length ? offered.map((variant) => variant.price ?? product.set_types.find((item) => item.id === variant.set_type_id)?.price ?? product.price) : [product.price];
  return { min: Math.min(...prices), max: Math.max(...prices) };
};

/** "Kurta + Dupatta · Size M · Pink" — shared by bag, checkout, orders and messages. */
export const variantLabel = (item: { setType?: string | null; set_type?: string | null; size?: string | null; color?: string | null }) =>
  [item.setType || item.set_type, item.size && `Size ${item.size}`, item.color].filter(Boolean).join(" · ");

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
    `Hello SAFYRA, I need help before submitting my order request. My bag contains: ${items
      .map((item) => `${item.title} (${variantLabel(item)}) x${item.quantity}`)
      .join(", ")}. Estimated total: ${formatPrice(total)}.`,
  );

/** Keyword → approximate swatch, mirroring backend lib/colors.py so admin previews match the storefront. */
const SWATCH_KEYWORDS: [string[], string][] = [
  [["ivory", "vanilla", "off white", "offwhite", "cream", "pearl"], "#EFE6D4"],
  [["white", "chalk"], "#F6F3EC"],
  [["blush", "rose", "pink", "petal"], "#D9A3A5"],
  [["peach", "coral", "apricot"], "#E7B49A"],
  [["red", "scarlet", "crimson", "maroon", "wine"], "#9B2F2A"],
  [["mustard", "butter", "yellow", "gold", "haldi"], "#DFBB55"],
  [["orange", "rust", "terracotta"], "#C2693C"],
  [["mint", "sage", "olive", "green", "pista", "emerald"], "#6F8166"],
  [["teal", "turquoise", "aqua"], "#4E8A8B"],
  [["sky", "aster", "powder blue", "blue", "indigo", "denim"], "#8CA7BF"],
  [["navy", "midnight", "ink"], "#2B3449"],
  [["lilac", "lavender", "mauve", "purple", "violet"], "#B4A3C4"],
  [["beige", "sand", "nude", "biscuit", "oat"], "#D9C7AC"],
  [["brown", "coffee", "chocolate", "mocha", "tan"], "#7B5A42"],
  [["grey", "gray", "silver", "steel"], "#9A9A96"],
  [["black", "onyx", "charcoal"], "#2A2724"],
];

export function swatchFor(name: string): string {
  const text = (name || "").trim().toLowerCase();
  if (!text) return "#E9DFC9";
  for (const [keywords, hex] of SWATCH_KEYWORDS) if (keywords.some((keyword) => text.includes(keyword))) return hex;
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) hash = (hash * 31 + text.charCodeAt(index)) >>> 0;
  const channel = (shift: number) => 110 + ((hash >> shift) & 0xff) % 90;
  return `#${[channel(0), channel(8), channel(16)].map((value) => value.toString(16).padStart(2, "0")).join("").toUpperCase()}`;
}

export const colorOption = (product: Pick<Product, "color_options">, color: string) =>
  product.color_options?.find((option) => option.name.toLowerCase() === (color || "").toLowerCase());

export const colorSwatch = (product: Pick<Product, "color_options">, color: string) =>
  colorOption(product, color)?.swatch || swatchFor(color);

/** Photos for a colour: its manually assigned images, falling back to the full product gallery. */
export function galleryFor(product: Pick<Product, "color_options" | "image_urls" | "image_url">, color: string): string[] {
  const assigned = colorOption(product, color)?.image_urls?.filter(Boolean) ?? [];
  if (assigned.length) return assigned;
  return product.image_urls?.length ? product.image_urls : [product.image_url];
}
