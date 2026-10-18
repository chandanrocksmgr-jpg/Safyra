import { useState, type ImgHTMLAttributes } from "react";

interface SafeProductImageProps extends ImgHTMLAttributes<HTMLImageElement> {
  productName: string;
  /** Tried in order when `src` fails, so one broken photo never blanks the product. */
  fallbackSrcs?: string[];
  /** Render nothing (instead of the branded placeholder) once every source fails. */
  hideWhenUnavailable?: boolean;
}

export default function SafeProductImage({ productName, alt, onError, src, fallbackSrcs, hideWhenUnavailable, ...props }: SafeProductImageProps) {
  const sources = [src, ...(fallbackSrcs ?? [])].filter((value, index, all): value is string => typeof value === "string" && value.trim() !== "" && all.indexOf(value) === index);
  const sourceKey = sources.join("|");
  // Failure state is tied to the current source list, so a new or re-ordered image is always retried.
  const [failure, setFailure] = useState({ sourceKey, count: 0 });
  const failedCount = failure.sourceKey === sourceKey ? failure.count : 0;
  const current = sources[failedCount];
  if (!current) {
    if (hideWhenUnavailable) return null;
    return <div className={`${props.className ?? ""} image-fallback`} role="img" aria-label={`Image unavailable for ${productName}`}><span>SAFYRA</span><small>Image awaiting update</small></div>;
  }
  return <img {...props} key={current} src={current} alt={alt} onError={(event) => { setFailure({ sourceKey, count: failedCount + 1 }); onError?.(event); }} />;
}
