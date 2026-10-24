import { MessageCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import BrandHeader from "@/components/BrandHeader";
import Seo from "@/components/Seo";
import SafeProductImage from "@/components/SafeProductImage";
import { apiGet } from "@/lib/api";
import type { AboutContent } from "@/lib/about";
import { whatsappUrl } from "@/lib/shop";

export default function About() {
  // Content is editable by the Super Admin in Admin → Brand story.
  const { data } = useQuery({ queryKey: ["about"], queryFn: () => apiGet<AboutContent>("/about") });
  if (!data) return <div className="page-shell"><BrandHeader /><main className="about-page"><p className="route-loading" data-testid="about-loading">Loading the SAFYRA story…</p></main></div>;
  const { founder } = data;
  return <div className="page-shell">
    <Seo title="About SAFYRA CHIKANKARI | Lucknowi Craft & Founder Story" description={data.intro} canonicalPath="/about" image={data.hero_image_url || undefined} />
    <BrandHeader />
    <main className="about-page">
      <header className="about-hero" data-testid="about-hero">
        <div>
          <span className="eyebrow">{data.eyebrow}</span>
          <h1>{data.title}{data.title_emphasis && <><br /><em>{data.title_emphasis}</em></>}</h1>
          <p>{data.intro}</p>
        </div>
        {data.hero_image_url && <SafeProductImage src={data.hero_image_url} alt="SAFYRA atelier" productName="SAFYRA" loading="eager" decoding="async" />}
      </header>

      {data.story_sections.map((section, index) => <section className={index % 2 ? "about-story is-reversed" : "about-story"} key={`${section.heading}-${index}`} data-testid={`about-story-${index}`}>
        {section.image_url && <SafeProductImage src={section.image_url} alt={section.heading} productName={section.heading} hideWhenUnavailable loading="lazy" decoding="async" />}
        <div><h2>{section.heading}</h2><p>{section.body}</p></div>
      </section>)}

      {data.values.length > 0 && <section className="about-values" data-testid="about-values">
        {data.values_title && <h2>{data.values_title}</h2>}
        <div className="about-value-grid">{data.values.map((value, index) => <article key={`${value.title}-${index}`} data-testid={`about-value-${index}`}><h3>{value.title}</h3><p>{value.body}</p></article>)}</div>
      </section>}

      {(founder.name || founder.body || founder.quote) && <section className="about-founder" data-testid="about-founder">
        {founder.image_url && <SafeProductImage src={founder.image_url} alt={founder.name} productName={founder.name || "SAFYRA founder"} hideWhenUnavailable loading="lazy" decoding="async" />}
        <div>
          <span className="eyebrow">Founder</span>
          {founder.quote && <blockquote data-testid="about-founder-quote">{founder.quote}</blockquote>}
          {founder.body && <p>{founder.body}</p>}
          {founder.name && <p className="about-founder-name" data-testid="about-founder-name"><strong>{founder.name}</strong>{founder.role && <span>{founder.role}</span>}</p>}
        </div>
      </section>}

      <a className="information-help" href={whatsappUrl(data.cta_message)} target="_blank" rel="noreferrer" data-testid="about-whatsapp"><MessageCircle size={17} /> {data.cta_label}</a>
    </main>
  </div>;
}
