import { useRef, useState } from "react";
import { ArrowDown, ArrowUp, ImagePlus, Link as LinkIcon, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import SafeProductImage from "@/components/SafeProductImage";
import { apiUpload, ApiError } from "@/lib/api";
import type { MediaUploadResponse } from "@/lib/cms";

interface ImageManagerProps {
  images: string[];
  onChange: (images: string[]) => void;
  label: string;
  testId: string;
  limit?: number;
}

export default function ImageManager({ images, onChange, label, testId, limit = 40 }: ImageManagerProps) {
  const [url, setUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const addUrl = () => {
    const next = url.trim();
    if (!next || images.includes(next) || images.length >= limit) return;
    onChange([...images, next]);
    setUrl("");
  };
  const upload = async (files?: FileList | null) => {
    const selected = Array.from(files ?? []).slice(0, Math.max(0, limit - images.length));
    if (!selected.length) return;
    setUploading(true);
    const uploadedUrls: string[] = [];
    let failed = 0;
    for (const file of selected) {
      const formData = new FormData();
      formData.append("file", file);
      try {
        const uploaded = await apiUpload<MediaUploadResponse>("/media/upload", formData);
        uploadedUrls.push(uploaded.url);
      } catch (reason) {
        failed += 1;
        toast.error(reason instanceof ApiError && reason.status === 413 ? `${file.name} must be 8 MB or smaller` : `${file.name} could not be uploaded`);
      }
    }
    if (uploadedUrls.length) {
      onChange([...images, ...uploadedUrls]);
      toast.success(`${uploadedUrls.length} ${uploadedUrls.length === 1 ? "image" : "images"} uploaded`);
    }
    if (failed && uploadedUrls.length) toast.warning(`${failed} ${failed === 1 ? "image was" : "images were"} skipped`);
    setUploading(false);
    if (inputRef.current) inputRef.current.value = "";
  };
  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= images.length) return;
    const next = [...images];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };
  return <section className="admin-image-manager" data-testid={testId}>
    <div className="admin-field-heading"><div><strong data-testid={`${testId}-label`}>{label}</strong><small data-testid={`${testId}-help`}>The first image is used as the primary storefront image.</small></div><span data-testid={`${testId}-count`}>{images.length}/{limit}</span></div>
    <div className="admin-image-inputs">
      <label><LinkIcon size={15} /><input type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="Paste image URL" data-testid={`${testId}-url-input`} /></label>
      <button type="button" className="button button-outline" onClick={addUrl} disabled={!url.trim() || images.length >= limit} data-testid={`${testId}-add-url`}><ImagePlus size={15} /> Add URL</button>
      <label className="button button-dark admin-upload-button"><Upload size={15} /> {uploading ? "Uploading…" : "Upload images"}<input ref={inputRef} type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={(event) => upload(event.target.files)} disabled={uploading || images.length >= limit} data-testid={`${testId}-file-input`} /></label>
    </div>
    {images.length > 0 && <div className="admin-image-grid" data-testid={`${testId}-gallery`}>{images.map((image, index) => <div className="admin-image-item" key={`${image}-${index}`} data-testid={`${testId}-item-${index}`}><SafeProductImage src={image} alt={`${label} ${index + 1}`} productName={label} /><span>{index === 0 ? "Primary" : `${index + 1}`}</span><div><button type="button" onClick={() => move(index, -1)} disabled={index === 0} aria-label="Move image earlier" data-testid={`${testId}-move-up-${index}`}><ArrowUp size={14} /></button><button type="button" onClick={() => move(index, 1)} disabled={index === images.length - 1} aria-label="Move image later" data-testid={`${testId}-move-down-${index}`}><ArrowDown size={14} /></button><button type="button" onClick={() => onChange(images.filter((_, itemIndex) => itemIndex !== index))} aria-label="Remove image" data-testid={`${testId}-remove-${index}`}><Trash2 size={14} /></button></div></div>)}</div>}
  </section>;
}