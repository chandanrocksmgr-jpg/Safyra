import { useRef, useState } from "react";
import { Film, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";

interface VideoManagerProps {
  videos: string[];
  onChange: (next: string[]) => void;
}

const LIMIT = 2;

/** Up to two product films: upload an MP4/WebM/MOV, or paste a link. */
export default function VideoManager({ videos, onChange }: VideoManagerProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [link, setLink] = useState("");

  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
    const room = LIMIT - videos.length;
    if (room <= 0) { toast.error("A product can show two videos at most"); return; }
    setUploading(true);
    const added: string[] = [];
    try {
      for (const file of Array.from(files).slice(0, room)) {
        const body = new FormData();
        body.append("file", file);
        const response = await fetch("/api/media/upload-video", { method: "POST", body, credentials: "include" });
        if (!response.ok) throw new ApiError(response.status, await response.json().catch(() => null));
        const payload = (await response.json()) as { url: string };
        added.push(payload.url);
      }
      onChange([...videos, ...added].slice(0, LIMIT));
      toast.success(added.length === 1 ? "Video uploaded" : `${added.length} videos uploaded`);
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
    onChange([...videos, url]);
    setLink("");
  };

  return <div className="video-manager" data-testid="admin-video-manager">
    <div className="variant-block-heading"><div><strong><Film size={15} /> Product videos</strong><small>Up to two short films shown on the product page. MP4, WebM or MOV, 40 MB each.</small></div></div>
    <div className="video-manager-list">
      {videos.map((url, index) => <div className="video-manager-item" key={url} data-testid={`admin-video-${index}`}>
        <video src={url} controls preload="metadata" playsInline />
        <div>
          <span>Video {index + 1}</span>
          <button type="button" className="link-button is-danger" onClick={() => onChange(videos.filter((_, position) => position !== index))} data-testid={`admin-video-remove-${index}`}><Trash2 size={14} /> Remove</button>
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
