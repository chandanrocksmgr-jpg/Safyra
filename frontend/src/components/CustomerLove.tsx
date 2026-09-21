const customerStories = [
  {
    name: "Rashmi",
    city: "Himachal Pradesh",
    image: "https://customer-assets-agu9un31.emergentagent.net/job_lucknowi-craft/artifacts/kta9w9ao_Screenshot_20260922-040533_WhatsApp%C2%A0Business.png",
    quote: "Hey Afira!\n\nI’m here flaunting yet another masterpiece “MAAHEEM” of Safyra. This dreamy soft pink, the delicate embroidery, and those intricate pearl and cutdana details—everything is so beautifully done.\n\nThe moment I wore it, I genuinely felt a little more glowy and beautiful. It’s one of those pieces that instantly makes you feel special.\nKeep creating magic—you’re truly doing an amazing job!",
  },
  {
    name: "Dr Manaswini",
    city: "Odisha",
    image: "https://customer-assets-agu9un31.emergentagent.net/job_lucknowi-craft/artifacts/8e39aozc_Screenshot_20260922-035727_WhatsApp%C2%A0Business.png",
    quote: "thank u for the beautiful peacock dress",
  },
  {
    name: "Kritika",
    city: "Bangkok",
    image: "https://customer-assets-agu9un31.emergentagent.net/job_lucknowi-craft/artifacts/xr6twi52_Screenshot_20260922-035659_WhatsApp%C2%A0Business.png",
    quote: "Beautiful such a perfect size thanks safyra",
  },
  {
    name: "Pranjal",
    city: "Bangalore",
    image: "https://customer-assets-agu9un31.emergentagent.net/job_lucknowi-craft/artifacts/48vneumx_Screenshot_20260922-040038_WhatsApp%C2%A0Business.webp",
    quote: "Every piece is more beautiful than the last. Each one is different and unique in its own way.\n\nI have no words to describe the fabric—it’s top quality. Whether it’s Mul Chanderi, cotton, viscose, or organza, every fabric feels amazing.\n\nI can’t wait to get them stitched and style them.\n\nThanks so much for all your help in choosing the colors!",
  },
  {
    name: "Supriya",
    city: "Delhi",
    image: "https://customer-assets-agu9un31.emergentagent.net/job_lucknowi-craft/artifacts/bgavczv7_Screenshot_20260922-040735_WhatsApp%C2%A0Business.png",
    quote: "Unfortunately, the person my dida bought this for couldn’t receive it, but this suit was actually on my manifestation list—and somehow, the universe made sure it found its way to me instead.\nAnd honestly, I’m so glad it did because this is SO, SO, SO, SO pretty and beautiful!\nAbsolutely in love with it. It feels like the universe sent me a little gift of my own.",
  },
];

export default function CustomerLove() {
  return <section className="section customer-love-section" data-testid="customer-love-section">
    <div className="customer-love-heading">
      <h2 data-testid="customer-love-heading">WORN. LOVED. RETURNED TO.</h2>
      <p data-testid="customer-love-subheading">Real women. Real SAFYRA. Real words.</p>
    </div>
    <div className="customer-love-grid">
      {customerStories.map((story, index) => <article className="customer-love-card" key={story.name} data-testid={`customer-love-card-${index + 1}`}>
        <div className="customer-love-image"><img src={story.image} alt={`${story.name} wearing SAFYRA`} loading="lazy" /></div>
        <div className="customer-love-copy">
          <blockquote data-testid={`customer-love-quote-${index + 1}`}>{story.quote}</blockquote>
          <p data-testid={`customer-love-customer-${index + 1}`}><strong>{story.name}</strong><span>{story.city}</span></p>
        </div>
      </article>)}
    </div>
  </section>;
}