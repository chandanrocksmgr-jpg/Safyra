import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import SafeProductImage from "@/components/SafeProductImage";

interface ProductImageViewerProps {
  images: string[];
  initialIndex: number;
  title: string;
  onClose: () => void;
  onIndexChange?: (index: number) => void;
}

interface Zoom { scale: number; x: number; y: number }
type GestureMode = "none" | "swipe" | "pan" | "pinch";

const RESET: Zoom = { scale: 1, x: 0, y: 0 };
const MAX_SCALE = 4;
const DOUBLE_TAP_SCALE = 2.5;
const DOUBLE_TAP_MS = 320;
const SWIPE_SHARE = 0.18;
const MAX_DOTS = 12;

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const clampPan = (zoom: Zoom, rect: DOMRect): Zoom => {
  const maxX = (rect.width * (zoom.scale - 1)) / 2;
  const maxY = (rect.height * (zoom.scale - 1)) / 2;
  return { scale: zoom.scale, x: clamp(zoom.x, -maxX, maxX), y: clamp(zoom.y, -maxY, maxY) };
};

/** Full-screen gallery: swipe between photos, pinch or double-tap to zoom, drag to pan. */
export default function ProductImageViewer({ images, initialIndex, title, onClose, onIndexChange }: ProductImageViewerProps) {
  const [index, setIndex] = useState(clamp(initialIndex, 0, images.length - 1));
  const [zoom, setZoomState] = useState<Zoom>(RESET);
  const [dragX, setDragX] = useState(0);
  const [dragging, setDragging] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef<Zoom>(RESET);
  const gesture = useRef({
    pointers: new Map<number, { x: number; y: number }>(),
    mode: "none" as GestureMode,
    startX: 0, startY: 0, startTime: 0, startDistance: 1, startZoom: RESET, moved: false, lastTap: 0,
  });

  const setZoom = (next: Zoom) => { zoomRef.current = next; setZoomState(next); };
  const go = useCallback((next: number) => {
    const target = clamp(next, 0, images.length - 1);
    zoomRef.current = RESET;
    setZoomState(RESET);
    setIndex(target);
    onIndexChange?.(target);
  }, [images.length, onIndexChange]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowRight") go(index + 1);
      if (event.key === "ArrowLeft") go(index - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = previousOverflow; window.removeEventListener("keydown", onKey); };
  }, [go, index, onClose]);

  const pinchDistance = () => {
    const [first, second] = [...gesture.current.pointers.values()];
    return Math.hypot(first.x - second.x, first.y - second.y) || 1;
  };
  const beginSinglePointer = (x: number, y: number) => {
    const g = gesture.current;
    g.mode = zoomRef.current.scale > 1 ? "pan" : "swipe";
    g.startX = x; g.startY = y; g.startZoom = zoomRef.current;
  };
  const toggleZoomAt = (clientX: number, clientY: number, rect: DOMRect) => {
    if (zoomRef.current.scale > 1) { setZoom(RESET); return; }
    const centreX = rect.left + rect.width / 2;
    const centreY = rect.top + rect.height / 2;
    // Keep the tapped point under the finger: translate = (centre - point) * (scale - 1)
    setZoom(clampPan({ scale: DOUBLE_TAP_SCALE, x: (centreX - clientX) * (DOUBLE_TAP_SCALE - 1), y: (centreY - clientY) * (DOUBLE_TAP_SCALE - 1) }, rect));
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    event.currentTarget.setPointerCapture(event.pointerId);
    g.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    setDragging(true);
    if (g.pointers.size === 2) {
      g.mode = "pinch"; g.startDistance = pinchDistance(); g.startZoom = zoomRef.current; g.moved = true;
      setDragX(0);
      return;
    }
    if (g.pointers.size === 1) {
      beginSinglePointer(event.clientX, event.clientY);
      g.startTime = Date.now(); g.moved = false;
    }
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    if (!g.pointers.has(event.pointerId)) return;
    g.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const rect = stageRef.current?.getBoundingClientRect();
    if (!rect) return;
    if (g.mode === "pinch" && g.pointers.size === 2) {
      const scale = clamp(g.startZoom.scale * (pinchDistance() / g.startDistance), 1, MAX_SCALE);
      setZoom(clampPan({ ...g.startZoom, scale }, rect));
      return;
    }
    const dx = event.clientX - g.startX;
    const dy = event.clientY - g.startY;
    if (Math.hypot(dx, dy) > 8) g.moved = true;
    if (g.mode === "pan") setZoom(clampPan({ scale: g.startZoom.scale, x: g.startZoom.x + dx, y: g.startZoom.y + dy }, rect));
    if (g.mode === "swipe") {
      const atEdge = (index === 0 && dx > 0) || (index === images.length - 1 && dx < 0);
      setDragX(atEdge ? dx * 0.3 : dx);
    }
  };

  const onPointerEnd = (event: ReactPointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    if (!g.pointers.has(event.pointerId)) return;
    g.pointers.delete(event.pointerId);
    const rect = stageRef.current?.getBoundingClientRect();
    if (g.mode === "pinch") {
      if (g.pointers.size === 1) {
        const [remaining] = [...g.pointers.values()];
        beginSinglePointer(remaining.x, remaining.y);
        return;
      }
      if (zoomRef.current.scale < 1.05) setZoom(RESET);
    } else if (g.pointers.size === 0 && rect) {
      const dx = event.clientX - g.startX;
      if (g.mode === "swipe" && g.moved) {
        if (dx < -rect.width * SWIPE_SHARE) go(index + 1);
        else if (dx > rect.width * SWIPE_SHARE) go(index - 1);
      }
      if (!g.moved && Date.now() - g.startTime < 300) {
        const now = Date.now();
        if (now - g.lastTap < DOUBLE_TAP_MS) { g.lastTap = 0; toggleZoomAt(event.clientX, event.clientY, rect); }
        else g.lastTap = now;
      }
    }
    if (g.pointers.size === 0) { g.mode = "none"; setDragX(0); setDragging(false); }
  };

  const zoomed = zoom.scale > 1;
  return <div className="image-viewer" role="dialog" aria-modal="true" aria-label={`${title} photos`} data-testid="product-image-viewer">
    <div className="image-viewer-top">
      <span className="image-viewer-counter" aria-live="polite" data-testid="image-viewer-counter">{index + 1} / {images.length}</span>
      <span className="image-viewer-title">{title}</span>
      <button type="button" className="image-viewer-close" onClick={onClose} aria-label="Close photo viewer" data-testid="image-viewer-close"><X size={20} /></button>
    </div>
    <div className="image-viewer-body">
      <div ref={stageRef} className={zoomed ? "image-viewer-stage is-zoomed" : "image-viewer-stage"} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerEnd} onPointerCancel={onPointerEnd} data-testid="image-viewer-stage">
        <div className={dragging ? "image-viewer-track is-dragging" : "image-viewer-track"} style={{ transform: `translate3d(calc(${-index * 100}% + ${dragX}px), 0, 0)` }}>
          {images.map((image, imageIndex) => <div className="image-viewer-slide" key={`${image}-${imageIndex}`} aria-hidden={imageIndex !== index}>
            {Math.abs(imageIndex - index) <= 1 && <SafeProductImage src={image} alt={`${title} photo ${imageIndex + 1}`} productName={title} draggable={false} className={dragging ? "is-dragging" : undefined} style={imageIndex === index ? { transform: `translate3d(${zoom.x}px, ${zoom.y}px, 0) scale(${zoom.scale})` } : undefined} data-testid={`image-viewer-image-${imageIndex + 1}`} />}
          </div>)}
        </div>
      </div>
      {images.length > 1 && <>
        <button type="button" className="image-viewer-nav is-prev" onClick={() => go(index - 1)} disabled={index === 0} aria-label="Previous photo" data-testid="image-viewer-prev"><ChevronLeft size={22} /></button>
        <button type="button" className="image-viewer-nav is-next" onClick={() => go(index + 1)} disabled={index === images.length - 1} aria-label="Next photo" data-testid="image-viewer-next"><ChevronRight size={22} /></button>
      </>}
    </div>
    <div className="image-viewer-bottom">
      <p className="image-viewer-hint" data-testid="image-viewer-hint">{zoomed ? "Drag to explore · double-tap to reset" : images.length > 1 ? "Pinch or double-tap to zoom · swipe for more" : "Pinch or double-tap to zoom"}</p>
      {images.length > 1 && images.length <= MAX_DOTS && <div className="image-viewer-dots">{images.map((image, imageIndex) => <button type="button" key={`${image}-dot-${imageIndex}`} className={imageIndex === index ? "is-active" : undefined} onClick={() => go(imageIndex)} aria-label={`Show photo ${imageIndex + 1}`} data-testid={`image-viewer-dot-${imageIndex + 1}`} />)}</div>}
    </div>
  </div>;
}
