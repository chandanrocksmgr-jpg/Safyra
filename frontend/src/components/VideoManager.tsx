import { useRef, useState } from "react";
import { Film, ImageDown, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import SafeProductImage from "@/components/SafeProductImage";

interface VideoManagerProps {
  videos: string[];
  posters: string[];
  gallery: string[];
  onChange: (videos: string[], posters: string[]) => void;
}

const LIMIT = 2;

/** Grabs a still from the chosen video file so the player never opens on a blank frame. */
async function captureStill(file: File): Promise<Blob | null> {
  const objectUrl = URL.createObjectURL(file);
  try {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.muted = true;
    video.playsInline = true;
    video.src = objectUrl;
    await new Promise<void>((resolve, reject) => {
      video.onloadeddata = () => resolve();
      video.onerror = () => reject(new Error("unreadable"));
      setTimeout(() => reject(new Error("timeout")), 8000);
    });
    video.currentTime = Math.min(1, (video.duration || 1) / 3);
    await new Promise<void>((resolve, reject) => {
      video.onseeked = () => resolve();
      video.onerror = () => reject(new Error("seek failed"));
      setTimeout(() => resolve(), 4000);
    });
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 720;
    canvas.height = video.videoHeight || 1280;
    const context = canvas.getContext("2d");
    if (!context) return null;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return await new Promise<Blob | null>((resolve) => canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.82));
  } catch {
    return null;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

async function uploadFile(path: string, file: File | Blob, filename: string): Promise<string> {
  const body = new FormData();
  body.append("file", file, filename);
  const response = await fetch(path, { method: "POST", body, credentials: "include" });
  if (!response.ok) throw new ApiError(response.status, await response.json().catch(() => null));
  const payload = (await response.json()) as { url?: string; urls?: string[] };
  return payload.url ?? payload.urls?.[0] ?? "";
}

/** Up to two product films, each with a poster still: upload an MP4/WebM/MOV, or paste a link. */
export default function VideoManager({ videos, posters, gallery, onChange }: VideoManagerProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [link, setLink] = useState("");

  const posterAt = (index: number) => posters[index] || "";

  const setPoster = (index: number, url: string) => {
    const next = [...posters];
    while (next.length < videos.length) next.push("");
    next[index] = url;
    onChange(videos, next);
  };

  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
    const room = LIMIT - videos.length;
    if (room <= 0) { toast.error("A product can show two videos at most"); return; }
    setUploading(true);
    const addedVideos: string[] = [];
    const addedPosters: string[] = [];
    try {
      for (const file of Array.from(files).slice(0, room)) {
        const url = await uploadFile("/api/media/upload-video", file, file.name);
        addedVideos.push(url);
        const still = await captureStill(file);
        if (still) {
          try {
            addedPosters.push(await uploadFile("/api/media/upload", still, `${file.name.replace(/\.[^.]+$/, "")}-cover.jpg`));
          } catch {
            addedPosters.push("");
          }
        } else {
          addedPosters.push("");
        }
      }
      const nextPosters = [...posters];
      while (nextPosters.length < videos.length) nextPosters.push("");
      onChange([...videos, ...addedVideos].slice(0, LIMIT), [...nextPosters, ...addedPosters].slice(0, LIMIT));
      toast.success(addedPosters.some(Boolean) ? "Video uploaded with a cover still" : "Video uploaded — pick a cover below");
    } catch (reason) {
      toast.error(reason instanceof ApiError ? String((reason.body as { detail?: string } | null)?.detail || "Upload failed") : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const addLink = () => {
    const url = link.trim();
    if (!url) return;
    if (videos.length >= LIMIT) { toast.error("A product can show two videos at most"); return; }
    const nextPosters = [...posters];
    while (nextPosters.length < videos.length) nextPosters.push("");
    onChange([...videos, url], [...nextPosters, gallery[0] ?? ""]);
    setLink("");
  };

  const remove = (index: number) => onChange(videos.filter((_, position) => position !== index), posters.filter((_, position) => position !== index));

  return <div className="video-manager" data-testid="admin-video-manager">
    <div className="variant-block-heading"><div><strong><Film size={15} /> Product videos</strong><small>Up to two short films shown on the product page. MP4, WebM or MOV, 40 MB each. A cover still is captured automatically — or choose a gallery photo instead.</small></div></div>
    <div className="video-manager-list">
      {videos.map((url, index) => <div className="video-manager-item" key={url} data-testid={`admin-video-${index}`}>
        <video src={url} poster={posterAt(index) || undefined} controls preload="metadata" playsInline />
        <div>
          <span>Video {index + 1}</span>
          <button type="button" className="link-button is-danger" onClick={() => remove(index)} data-testid={`admin-video-remove-${index}`}><Trash2 size={14} /> Remove</button>
        </div>
        <div className="video-poster-picker">
          <span><ImageDown size={13} /> Cover still</span>
          <div className="video-poster-options">
            {posterAt(index) && !gallery.includes(posterAt(index)) && <button type="button" className="color-photo-pick is-picked" title="Captured from the video" data-testid={`admin-video-poster-captured-${index}`}><SafeProductImage src={posterAt(index)} alt="Captured cover" productName="Video cover" /><em>Auto</em></button>}
            {gallery.slice(0, 6).map((photo, photoIndex) => <button type="button" key={photo} className={posterAt(index) === photo ? "color-photo-pick is-picked" : "color-photo-pick"} onClick={() => setPoster(index, posterAt(index) === photo ? "" : photo)} title={`Use photo ${photoIndex + 1} as the cover`} data-testid={`admin-video-poster-${index}-${photoIndex}`}><SafeProductImage src={photo} alt={`Photo ${photoIndex + 1}`} productName="Video cover" /></button>)}
          </div>
        </div>
      </div>)}
    </div>
    <div className="video-manager-actions">
      <label className="button button-dark admin-upload-button"><Upload size={15} /> {uploading ? "Uploading…" : "Upload video"}
        <input ref={inputRef} type="file" accept="video/mp4,video/webm,video/quicktime" onChange={(event) => upload(event.target.files)} disabled={uploading || videos.length >= LIMIT} data-testid="admin-video-file-input" />
      </label>
      <input value={link} onChange={(event) => setLink(event.target.value)} placeholder="…or paste a video link" data-testid="admin-video-link-input" />
      <button type="button" className="button button-outline" onClick={addLink} disabled={!link.trim() || videos.length >= LIMIT} data-testid="admin-video-link-add">Add link</button>
    </div>
    {videos.length >= LIMIT && <p className="admin-help-text" data-testid="admin-video-limit-note">Two videos added — remove one to replace it.</p>}
  </div>;
}
