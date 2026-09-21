import { useState, type ImgHTMLAttributes } from "react";

interface SafeProductImageProps extends ImgHTMLAttributes<HTMLImageElement> {
  productName: string;
}

export default function SafeProductImage({ productName, alt, onError, ...props }: SafeProductImageProps) {
  const [failed, setFailed] = useState(false);
  if (failed) return <div className={`${props.className ?? ""} image-fallback`} role="img" aria-label={`Image unavailable for ${productName}`}><span>SAFYRA</span><small>Image awaiting update</small></div>;
  return <img {...props} alt={alt} onError={(event) => { setFailed(true); onError?.(event); }} />;
}