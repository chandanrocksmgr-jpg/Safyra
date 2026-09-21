import { useEffect } from "react";

interface SeoProps {
  title: string;
  description: string;
  canonicalPath?: string;
  image?: string;
  structuredData?: Record<string, unknown> | Array<Record<string, unknown>>;
}

const SITE_URL = "https://safyra.co";
const DEFAULT_IMAGE = "https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=1800";

function setMeta(attribute: "name" | "property", key: string, content: string) {
  let element = document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`);
  if (!element) {
    element = document.createElement("meta");
    element.setAttribute(attribute, key);
    document.head.appendChild(element);
  }
  element.content = content;
}

export default function Seo({ title, description, canonicalPath = "/", image, structuredData }: SeoProps) {
  useEffect(() => {
    const canonicalUrl = `${SITE_URL}${canonicalPath}`;
    document.title = title;
    setMeta("name", "description", description);
    setMeta("property", "og:title", title);
    setMeta("property", "og:description", description);
    setMeta("property", "og:type", canonicalPath.startsWith("/product/") ? "product" : "website");
    setMeta("property", "og:url", canonicalUrl);
    setMeta("name", "twitter:card", "summary_large_image");
    setMeta("property", "og:image", image || DEFAULT_IMAGE);
    setMeta("name", "twitter:image", image || DEFAULT_IMAGE);
    let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.rel = "canonical";
      document.head.appendChild(canonical);
    }
    canonical.href = canonicalUrl;
    const scriptId = "safyra-structured-data";
    document.getElementById(scriptId)?.remove();
    if (structuredData) {
      const script = document.createElement("script");
      script.id = scriptId;
      script.type = "application/ld+json";
      script.text = JSON.stringify(structuredData);
      document.head.appendChild(script);
    }
  }, [canonicalPath, description, image, structuredData, title]);
  return null;
}