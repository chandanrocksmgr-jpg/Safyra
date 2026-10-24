import { MessageCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import BrandHeader from "@/components/BrandHeader";
import Seo from "@/components/Seo";
import { apiGet } from "@/lib/api";
import type { InformationContent } from "@/lib/information";
import { whatsappUrl } from "@/lib/shop";

export default function Information() {
  // Content is editable by the Super Admin in Admin → Care & information.
  const { data } = useQuery({ queryKey: ["information"], queryFn: () => apiGet<InformationContent>("/information") });
  if (!data) return <div className="page-shell"><BrandHeader /><main className="information-page"><p className="route-loading" data-testid="information-loading">Loading guidance…</p></main></div>;
  return <div className="page-shell">
    <Seo title="Delivery, Care & Chikankari Information | SAFYRA" description="Read SAFYRA guidance for product details, Chikankari work, dispatch, delivery, garment care, exchanges and customer support." canonicalPath="/information" />
    <BrandHeader />
    <main className="information-page">
      <header><span className="eyebrow">{data.eyebrow}</span><h1>{data.title}{data.title_emphasis && <><br /><em>{data.title_emphasis}</em></>}</h1><p>{data.intro}</p></header>
      <nav className="information-nav">
        {data.sections.map((section) => <a href={`#${section.id}`} key={section.id} data-testid={`information-nav-${section.id}`}>{section.label}</a>)}
        {data.faqs.length > 0 && <a href="#faq" data-testid="information-nav-faq">FAQ</a>}
      </nav>
      {data.sections.map((section) => <section id={section.id} className="information-section" key={section.id} data-testid={`information-section-${section.id}`}>
        <span className="eyebrow">{section.label}</span><h2>{section.title}</h2><p>{section.text}</p>
      </section>)}
      {data.faqs.length > 0 && <section id="faq" className="information-section faq-section" data-testid="information-faq">
        <span className="eyebrow">Frequently asked questions</span><h2>{data.faq_title}</h2>
        {data.faqs.map((faq, index) => <details key={faq.question} open={index === 0} data-testid={`information-faq-${index}`}><summary>{faq.question}</summary><p>{faq.answer}</p></details>)}
      </section>}
      <a className="information-help" href={whatsappUrl(data.help_message)} target="_blank" rel="noreferrer" data-testid="information-whatsapp"><MessageCircle size={17} /> {data.help_label}</a>
    </main>
  </div>;
}
