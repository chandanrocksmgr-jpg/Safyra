export type PublishingStatus = "draft" | "active" | "archived";
export type CatalogGroupType = "category" | "collection";

export interface CatalogGroup {
  id: string;
  name: string;
  slug: string;
  group_type: CatalogGroupType;
  description: string;
  image_url: string;
  status: PublishingStatus;
  sort_order: number;
  show_on_home: boolean;
  created_at: string;
  updated_at: string;
}

export interface MediaUploadResponse {
  url: string;
  filename: string;
  content_type: string;
  size: number;
}

export interface HomepageHero {
  eyebrow: string;
  title: string;
  emphasis: string;
  body: string;
  image_url: string;
  primary_label: string;
  primary_url: string;
  secondary_label: string;
  secondary_url: string;
}

export interface HomepageStory {
  eyebrow: string;
  title: string;
  body: string;
  image_url: string;
  link_label: string;
  link_url: string;
}

export interface HomepageSections {
  show_new_arrivals: boolean;
  show_categories: boolean;
  show_best_sellers: boolean;
  show_luxury: boolean;
  show_collections: boolean;
  show_customer_love: boolean;
  show_story: boolean;
  show_whatsapp: boolean;
}

export interface HomepageSettings {
  id: string;
  announcement_messages: string[];
  hero: HomepageHero;
  sections: HomepageSections;
  new_arrivals_eyebrow: string;
  new_arrivals_title: string;
  categories_eyebrow: string;
  categories_title: string;
  best_sellers_eyebrow: string;
  best_sellers_title: string;
  collections_eyebrow: string;
  collections_title: string;
  luxury_eyebrow: string;
  story: HomepageStory;
  whatsapp_eyebrow: string;
  whatsapp_title: string;
  updated_at: string;
}

export const defaultHomepage: HomepageSettings = {
  id: "homepage",
  announcement_messages: [
    "FREE SHIPPING ON ORDERS ABOVE ₹1,299",
    "A LITTLE SOMETHING FROM SAFYRA — WITH YOUR FIRST ORDER",
  ],
  hero: {
    eyebrow: "Lucknowi Chikankari",
    title: "Chikankari,",
    emphasis: "made to be remembered.",
    body: "Handcrafted Chikankari, created by skilled artisans in Lucknow.",
    image_url: "https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=1800",
    primary_label: "Shop new arrivals",
    primary_url: "/shop?new=true&sort=newest",
    secondary_label: "Shop SAFYRA Luxury",
    secondary_url: "/shop?collection=Safyra%20Luxury",
  },
  sections: {
    show_new_arrivals: true,
    show_categories: true,
    show_best_sellers: true,
    show_luxury: true,
    show_collections: true,
    show_customer_love: true,
    show_story: true,
    show_whatsapp: true,
  },
  new_arrivals_eyebrow: "Just added",
  new_arrivals_title: "Shop new arrivals",
  categories_eyebrow: "Choose a silhouette",
  categories_title: "Shop by category",
  best_sellers_eyebrow: "Customer favourites",
  best_sellers_title: "Bestsellers",
  collections_eyebrow: "Current collections",
  collections_title: "Shop by collection",
  luxury_eyebrow: "SAFYRA Luxury",
  story: {
    eyebrow: "SAFYRA, Lucknow",
    title: "A focused Chikankari wardrobe.",
    body: "SAFYRA works with Lucknowi Chikankari across Indian silhouettes and verified fabrics. Each product page brings the textile, embroidery description, fit and making information together in one place.",
    image_url: "https://safyra.co/cdn/shop/files/IMG_3973.jpg?v=1772064171&width=1200",
    link_label: "About the craft",
    link_url: "/information#craft",
  },
  whatsapp_eyebrow: "Customer care",
  whatsapp_title: "Personal help, before you order.",
  updated_at: "",
};