import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileEdit, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import { apiGet, apiPut } from "@/lib/api";
import type { AboutContent, AboutStorySection, AboutValue } from "@/lib/about";

export default function AdminAbout() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["about"], queryFn: () => apiGet<AboutContent>("/about") });
  const [draft, setDraft] = useState<AboutContent | null>(null);
  useEffect(() => { if (data && !draft) setDraft(data); }, [data, draft]);

  const save = useMutation({
    mutationFn: (content: AboutContent) => apiPut<AboutContent>("/about", content),
    onSuccess: (content) => { setDraft(content); void queryClient.invalidateQueries({ queryKey: ["about"] }); toast.success("Brand story page updated"); },
    onError: () => toast.error("Could not save this content"),
  });

  if (!draft) return <AdminShell eyebrow="Storefront content" title="Brand story." description="Loading the live page content."><p>Loading…</p></AdminShell>;

  const patch = (changes: Partial<AboutContent>) => setDraft({ ...draft, ...changes });
  const patchStory = (index: number, changes: Partial<AboutStorySection>) => patch({ story_sections: draft.story_sections.map((section, position) => position === index ? { ...section, ...changes } : section) });
  const patchValue = (index: number, changes: Partial<AboutValue>) => patch({ values: draft.values.map((value, position) => position === index ? { ...value, ...changes } : value) });

  return <AdminShell eyebrow="Storefront content" title="Brand story & founder." description="Edit every word and image on the customer-facing About page.">
    <section className="admin-dashboard-section" data-testid="admin-about-header-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">Page header</span><h2>Headline & intro</h2></div><FileEdit size={22} /></div>
      <div className="admin-form-grid">
        <label>Eyebrow<input value={draft.eyebrow} onChange={(event) => patch({ eyebrow: event.target.value })} data-testid="admin-about-eyebrow" /></label>
        <label>Headline<input value={draft.title} onChange={(event) => patch({ title: event.target.value })} data-testid="admin-about-title" /></label>
        <label>Headline second line<input value={draft.title_emphasis} onChange={(event) => patch({ title_emphasis: event.target.value })} data-testid="admin-about-title-emphasis" /></label>
        <label>Hero image URL<input value={draft.hero_image_url} onChange={(event) => patch({ hero_image_url: event.target.value })} placeholder="/api/media/…" data-testid="admin-about-hero-image" /></label>
        <label className="is-wide">Intro<textarea rows={2} value={draft.intro} onChange={(event) => patch({ intro: event.target.value })} data-testid="admin-about-intro" /></label>
      </div>
    </section>

    <section className="admin-dashboard-section" data-testid="admin-about-story-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">Craft & artisan story</span><h2>{draft.story_sections.length} story blocks</h2></div>
        <button type="button" className="button" onClick={() => patch({ story_sections: [...draft.story_sections, { heading: "New chapter", body: "Tell this part of the story.", image_url: "" }] })} data-testid="admin-about-add-story"><Plus size={14} /> Add block</button></div>
      <div className="admin-information-list">
        {draft.story_sections.map((section, index) => <div className="admin-information-card" key={index} data-testid={`admin-about-story-${index}`}>
          <div className="admin-form-grid">
            <label>Heading<input value={section.heading} onChange={(event) => patchStory(index, { heading: event.target.value })} data-testid={`admin-about-story-heading-${index}`} /></label>
            <label>Image URL<input value={section.image_url} onChange={(event) => patchStory(index, { image_url: event.target.value })} placeholder="/api/media/…" data-testid={`admin-about-story-image-${index}`} /></label>
            <label className="is-wide">Body<textarea rows={3} value={section.body} onChange={(event) => patchStory(index, { body: event.target.value })} data-testid={`admin-about-story-body-${index}`} /></label>
          </div>
          <button type="button" className="link-button is-danger" onClick={() => patch({ story_sections: draft.story_sections.filter((_, position) => position !== index) })} data-testid={`admin-about-remove-story-${index}`}><Trash2 size={14} /> Remove block</button>
        </div>)}
      </div>
    </section>

    <section className="admin-dashboard-section" data-testid="admin-about-values-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">Why SAFYRA</span><h2>{draft.values.length} promises</h2></div>
        <button type="button" className="button" onClick={() => patch({ values: [...draft.values, { title: "New promise", body: "What this means for the customer." }] })} data-testid="admin-about-add-value"><Plus size={14} /> Add promise</button></div>
      <div className="admin-form-grid"><label className="is-wide">Section heading<input value={draft.values_title} onChange={(event) => patch({ values_title: event.target.value })} data-testid="admin-about-values-title" /></label></div>
      <div className="admin-information-list">
        {draft.values.map((value, index) => <div className="admin-information-card" key={index} data-testid={`admin-about-value-${index}`}>
          <div className="admin-form-grid">
            <label>Title<input value={value.title} onChange={(event) => patchValue(index, { title: event.target.value })} data-testid={`admin-about-value-title-${index}`} /></label>
            <label className="is-wide">Body<textarea rows={2} value={value.body} onChange={(event) => patchValue(index, { body: event.target.value })} data-testid={`admin-about-value-body-${index}`} /></label>
          </div>
          <button type="button" className="link-button is-danger" onClick={() => patch({ values: draft.values.filter((_, position) => position !== index) })} data-testid={`admin-about-remove-value-${index}`}><Trash2 size={14} /> Remove promise</button>
        </div>)}
      </div>
    </section>

    <section className="admin-dashboard-section" data-testid="admin-about-founder-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">Founder</span><h2>Founder story</h2></div></div>
      <div className="admin-form-grid">
        <label>Name<input value={draft.founder.name} onChange={(event) => patch({ founder: { ...draft.founder, name: event.target.value } })} data-testid="admin-about-founder-name" /></label>
        <label>Role<input value={draft.founder.role} onChange={(event) => patch({ founder: { ...draft.founder, role: event.target.value } })} data-testid="admin-about-founder-role" /></label>
        <label>Portrait image URL<input value={draft.founder.image_url} onChange={(event) => patch({ founder: { ...draft.founder, image_url: event.target.value } })} placeholder="/api/media/…" data-testid="admin-about-founder-image" /></label>
        <label className="is-wide">Pull quote<textarea rows={2} value={draft.founder.quote} onChange={(event) => patch({ founder: { ...draft.founder, quote: event.target.value } })} data-testid="admin-about-founder-quote" /></label>
        <label className="is-wide">Founder note<textarea rows={3} value={draft.founder.body} onChange={(event) => patch({ founder: { ...draft.founder, body: event.target.value } })} data-testid="admin-about-founder-body" /></label>
      </div>
    </section>

    <section className="admin-dashboard-section" data-testid="admin-about-cta-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">WhatsApp help</span><h2>Contact prompt</h2></div></div>
      <div className="admin-form-grid">
        <label>Button label<input value={draft.cta_label} onChange={(event) => patch({ cta_label: event.target.value })} data-testid="admin-about-cta-label" /></label>
        <label className="is-wide">Pre-filled WhatsApp message<textarea rows={2} value={draft.cta_message} onChange={(event) => patch({ cta_message: event.target.value })} data-testid="admin-about-cta-message" /></label>
      </div>
      <button className="button button-dark" disabled={save.isPending} onClick={() => save.mutate(draft)} data-testid="admin-about-save"><FileEdit size={15} /> Save page content</button>
    </section>
  </AdminShell>;
}
