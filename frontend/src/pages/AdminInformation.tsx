import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileEdit, Plus, Trash2, HelpCircle } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import { apiGet, apiPut } from "@/lib/api";
import type { InformationContent, InformationFaq, InformationSection } from "@/lib/information";

export default function AdminInformation() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["information"], queryFn: () => apiGet<InformationContent>("/information") });
  const [draft, setDraft] = useState<InformationContent | null>(null);
  useEffect(() => { if (data && !draft) setDraft(data); }, [data, draft]);

  const save = useMutation({
    mutationFn: (content: InformationContent) => apiPut<InformationContent>("/information", content),
    onSuccess: (content) => { setDraft(content); void queryClient.invalidateQueries({ queryKey: ["information"] }); toast.success("Care & information page updated"); },
    onError: () => toast.error("Could not save this content"),
  });

  if (!draft) return <AdminShell eyebrow="Storefront content" title="Care & information." description="Loading the live page content."><p>Loading…</p></AdminShell>;

  const patch = (changes: Partial<InformationContent>) => setDraft({ ...draft, ...changes });
  const patchSection = (index: number, changes: Partial<InformationSection>) => patch({ sections: draft.sections.map((section, position) => position === index ? { ...section, ...changes } : section) });
  const patchFaq = (index: number, changes: Partial<InformationFaq>) => patch({ faqs: draft.faqs.map((faq, position) => position === index ? { ...faq, ...changes } : faq) });

  return <AdminShell eyebrow="Storefront content" title="Care & information." description="Edit every word on the customer-facing care, delivery and FAQ page.">
    <section className="admin-dashboard-section" data-testid="admin-information-header-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">Page header</span><h2>Headline & intro</h2></div><FileEdit size={22} /></div>
      <div className="admin-form-grid">
        <label>Eyebrow<input value={draft.eyebrow} onChange={(event) => patch({ eyebrow: event.target.value })} data-testid="admin-information-eyebrow" /></label>
        <label>Headline<input value={draft.title} onChange={(event) => patch({ title: event.target.value })} data-testid="admin-information-title" /></label>
        <label>Headline second line<input value={draft.title_emphasis} onChange={(event) => patch({ title_emphasis: event.target.value })} data-testid="admin-information-title-emphasis" /></label>
        <label className="is-wide">Intro<textarea rows={2} value={draft.intro} onChange={(event) => patch({ intro: event.target.value })} data-testid="admin-information-intro" /></label>
      </div>
    </section>

    <section className="admin-dashboard-section" data-testid="admin-information-sections-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">Sections</span><h2>{draft.sections.length} tabs on the page</h2></div>
        <button type="button" className="button" onClick={() => patch({ sections: [...draft.sections, { id: `section-${draft.sections.length + 1}`, label: "New section", title: "Section headline", text: "Describe this topic." }] })} data-testid="admin-information-add-section"><Plus size={14} /> Add section</button></div>
      <div className="admin-information-list">
        {draft.sections.map((section, index) => <div className="admin-information-card" key={index} data-testid={`admin-information-section-${index}`}>
          <div className="admin-form-grid">
            <label>Tab label<input value={section.label} onChange={(event) => patchSection(index, { label: event.target.value })} data-testid={`admin-information-section-label-${index}`} /></label>
            <label>Anchor id<input value={section.id} onChange={(event) => patchSection(index, { id: event.target.value.trim().toLowerCase().replaceAll(" ", "-") })} data-testid={`admin-information-section-id-${index}`} /></label>
            <label className="is-wide">Headline<input value={section.title} onChange={(event) => patchSection(index, { title: event.target.value })} data-testid={`admin-information-section-title-${index}`} /></label>
            <label className="is-wide">Body<textarea rows={3} value={section.text} onChange={(event) => patchSection(index, { text: event.target.value })} data-testid={`admin-information-section-text-${index}`} /></label>
          </div>
          <button type="button" className="link-button is-danger" onClick={() => patch({ sections: draft.sections.filter((_, position) => position !== index) })} data-testid={`admin-information-remove-section-${index}`}><Trash2 size={14} /> Remove section</button>
        </div>)}
      </div>
    </section>

    <section className="admin-dashboard-section" data-testid="admin-information-faq-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">FAQ</span><h2>{draft.faqs.length} questions</h2></div>
        <button type="button" className="button" onClick={() => patch({ faqs: [...draft.faqs, { question: "New question", answer: "Answer shown to customers." }] })} data-testid="admin-information-add-faq"><HelpCircle size={14} /> Add question</button></div>
      <div className="admin-form-grid"><label className="is-wide">FAQ headline<input value={draft.faq_title} onChange={(event) => patch({ faq_title: event.target.value })} data-testid="admin-information-faq-title" /></label></div>
      <div className="admin-information-list">
        {draft.faqs.map((faq, index) => <div className="admin-information-card" key={index} data-testid={`admin-information-faq-${index}`}>
          <div className="admin-form-grid">
            <label className="is-wide">Question<input value={faq.question} onChange={(event) => patchFaq(index, { question: event.target.value })} data-testid={`admin-information-faq-question-${index}`} /></label>
            <label className="is-wide">Answer<textarea rows={3} value={faq.answer} onChange={(event) => patchFaq(index, { answer: event.target.value })} data-testid={`admin-information-faq-answer-${index}`} /></label>
          </div>
          <button type="button" className="link-button is-danger" onClick={() => patch({ faqs: draft.faqs.filter((_, position) => position !== index) })} data-testid={`admin-information-remove-faq-${index}`}><Trash2 size={14} /> Remove question</button>
        </div>)}
      </div>
    </section>

    <section className="admin-dashboard-section" data-testid="admin-information-help-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">WhatsApp help</span><h2>Contact prompt</h2></div></div>
      <div className="admin-form-grid">
        <label>Button label<input value={draft.help_label} onChange={(event) => patch({ help_label: event.target.value })} data-testid="admin-information-help-label" /></label>
        <label className="is-wide">Pre-filled WhatsApp message<textarea rows={2} value={draft.help_message} onChange={(event) => patch({ help_message: event.target.value })} data-testid="admin-information-help-message" /></label>
      </div>
      <button className="button button-dark" disabled={save.isPending} onClick={() => save.mutate(draft)} data-testid="admin-information-save"><FileEdit size={15} /> Save page content</button>
    </section>
  </AdminShell>;
}
