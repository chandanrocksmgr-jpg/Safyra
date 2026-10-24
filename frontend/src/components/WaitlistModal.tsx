import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, X } from "lucide-react";
import { toast } from "sonner";
import { apiPost, ApiError } from "@/lib/api";
import { variantLabel, type Product } from "@/lib/shop";
import type { WaitlistCreate, WaitlistSubmission } from "@/lib/waitlist";

function errorDetail(reason: unknown) {
  if (reason instanceof ApiError && reason.body && typeof reason.body === "object" && "detail" in reason.body) {
    const detail = (reason.body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return "We couldn’t save your request. Please review your details and try again.";
}

interface WaitlistSelection { setTypeId: string; size: string; color: string }

export default function WaitlistModal({ product, onClose, initial }: { product: Product; onClose: () => void; initial?: WaitlistSelection }) {
  const [form, setForm] = useState({ customer_name: "", mobile: "", email: "", size: initial?.size ?? "", color: initial?.color ?? "", set_type: initial?.setTypeId ?? product.set_types[0]?.id ?? "" });
  const needsSetType = product.set_types.length > 0;
  const [error, setError] = useState("");
  const [submission, setSubmission] = useState<WaitlistSubmission | null>(null);
  const needsSize = product.sizes.length > 0;
  const needsColor = product.colors.length > 1;
  const mutation = useMutation({
    mutationFn: (payload: WaitlistCreate) => apiPost<WaitlistSubmission>("/waitlist", payload),
    onSuccess: (result) => { setError(""); setSubmission(result); toast.success("You’re on the waitlist"); },
    onError: (reason) => setError(errorDetail(reason)),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError("");
    mutation.mutate({
      product_id: product.id,
      customer_name: form.customer_name.trim(),
      mobile: form.mobile.trim(),
      email: form.email.trim() || null,
      size: needsSize ? form.size : null,
      color: needsColor ? form.color : product.colors[0] ?? null,
      set_type: needsSetType ? form.set_type : null,
    });
  };

  return <div className="modal-layer waitlist-modal-layer" role="dialog" aria-modal="true" aria-labelledby="waitlist-title" data-testid="waitlist-modal">
    <button className="drawer-scrim" onClick={onClose} aria-label="Close waitlist" data-testid="waitlist-modal-scrim" />
    <div className="modal-card waitlist-card">
      <button className="waitlist-close" onClick={onClose} aria-label="Close waitlist" data-testid="waitlist-modal-close"><X size={19} /></button>
      {submission ? <div className="waitlist-success" data-testid="waitlist-success">
        <CheckCircle2 size={30} data-testid="waitlist-success-icon" />
        <span className="eyebrow" data-testid="waitlist-success-eyebrow">Request received</span>
        <h2 id="waitlist-title" data-testid="waitlist-success-title">You’re on the waitlist.</h2>
        <p data-testid="waitlist-success-copy">We’ve recorded your interest in {submission.product_title}{variantLabel(submission) ? ` (${variantLabel(submission)})` : ""}. SAFYRA will contact you personally when availability changes.</p>
        <button className="button button-dark button-full" onClick={onClose} data-testid="waitlist-success-close">Continue browsing</button>
      </div> : <>
        <span className="eyebrow" data-testid="waitlist-eyebrow">Limited availability</span>
        <h2 id="waitlist-title" data-testid="waitlist-title">Join the waitlist</h2>
        <p data-testid="waitlist-intro">Leave your details for <strong>{product.title}</strong>. We’ll reach out personally if this piece becomes available.</p>
        <form className="waitlist-form" onSubmit={submit} data-testid="waitlist-form">
          <label data-testid="waitlist-name-label">Name<input value={form.customer_name} onChange={(event) => setForm({ ...form, customer_name: event.target.value })} autoComplete="name" required minLength={2} data-testid="waitlist-name-input" /></label>
          <label data-testid="waitlist-mobile-label">Mobile number<input type="tel" value={form.mobile} onChange={(event) => setForm({ ...form, mobile: event.target.value })} placeholder="+91 98765 43210" autoComplete="tel" required data-testid="waitlist-mobile-input" /></label>
          <label className="waitlist-field-wide" data-testid="waitlist-email-label">Email <small>Optional</small><input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} autoComplete="email" data-testid="waitlist-email-input" /></label>
          {needsSetType && <label className="waitlist-field-wide" data-testid="waitlist-set-type-label">Set<select value={form.set_type} onChange={(event) => setForm({ ...form, set_type: event.target.value })} required data-testid="waitlist-set-type-select">{product.set_types.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>}
          {needsSize && <label data-testid="waitlist-size-label">Size<select value={form.size} onChange={(event) => setForm({ ...form, size: event.target.value })} required data-testid="waitlist-size-select"><option value="">Select size</option>{product.sizes.map((size) => <option value={size} key={size}>{size}</option>)}</select></label>}
          {needsColor && <label data-testid="waitlist-color-label">Colour<select value={form.color} onChange={(event) => setForm({ ...form, color: event.target.value })} required data-testid="waitlist-color-select"><option value="">Select colour</option>{product.colors.map((color) => <option value={color} key={color}>{color}</option>)}</select></label>}
          {error && <div className="form-error waitlist-field-wide" data-testid="waitlist-form-error">{error}</div>}
          <button className="button button-dark button-full waitlist-field-wide" disabled={mutation.isPending} data-testid="waitlist-submit-button">{mutation.isPending ? "Joining…" : "Join the waitlist"}</button>
          <small className="waitlist-privacy waitlist-field-wide" data-testid="waitlist-privacy-note">Your details are used only to follow up on this availability request. No automated message is sent.</small>
        </form>
      </>}
    </div>
  </div>;
}